// Global Application State
let appConfig = {
    demo_mode_active: true,
    camera_index: 0,
    decision_threshold: 85.0,
    inspection_mode: "PCB",
    demo_override: "None"
};

let defectChartInstance = null;
let currentHistoryData = [];
let lastScanResult = null; // Stores last scan metadata for report compilation

// Detect Cloud Mode (e.g. running on Vercel) vs Local Mode (localhost)
const isCloudMode = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';

// Initialize Page
document.addEventListener("DOMContentLoaded", () => {
    // Icons init
    lucide.createIcons();
    
    // Sync UI with config from Server
    fetchConfig();
    
    // Initialize Event Listeners
    setupConfigListeners();
    setupScannerListeners();
    setupDashboardListeners();
    
    // Initialize tab trigger callbacks
    setupTabTriggers();
    
    // Initial fetch of analytics and history data
    updateAnalytics();
    updateHistory();
});

// Tab Switcher Routine
function setupTabTriggers() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTabId = btn.getAttribute("data-tab");
            switchTab(targetTabId);
        });
    });
}

function switchTab(tabId) {
    // Toggle active tab buttons
    document.querySelectorAll(".tab-btn").forEach(btn => {
        if (btn.getAttribute("data-tab") === tabId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Toggle active panels
    document.querySelectorAll(".tab-panel").forEach(panel => {
        if (panel.id === tabId) {
            panel.classList.add("active");
        } else {
            panel.classList.remove("active");
        }
    });

    // Run tab-specific reload routines
    if (tabId === "tab-dashboard") {
        updateAnalytics();
    } else if (tabId === "tab-history") {
        updateHistory();
    }
}

// Config Synchronization
async function fetchConfig() {
    try {
        const response = await fetch("/api/config");
        if (response.ok) {
            appConfig = await response.json();
            syncConfigToUI();
        }
        
        // Fetch cameras if demo mode is off
        await updateCameraSelector();
    } catch (err) {
        console.error("Failed to fetch backend configuration:", err);
    }
}

function syncConfigToUI() {
    // Sidebar bindings
    document.getElementById("demo-mode-toggle").checked = appConfig.demo_mode_active;
    document.getElementById("threshold-slider").value = appConfig.decision_threshold;
    document.getElementById("threshold-val").innerText = appConfig.decision_threshold.toFixed(1) + "%";
    
    // Scanner Control Panel bindings
    document.getElementById("inspection-mode").value = appConfig.inspection_mode;
    document.getElementById("override-select").value = appConfig.demo_override;
    
    // Sync displays
    toggleCameraSelectVisibility(appConfig.demo_mode_active);
    updateSystemHealthDisplay();
}

function toggleCameraSelectVisibility(demoModeActive) {
    const cameraSelectGroup = document.getElementById("camera-select-group");
    // Only show camera index selector in local mode when demo mode is inactive
    if (demoModeActive || isCloudMode) {
        cameraSelectGroup.style.display = "none";
    } else {
        cameraSelectGroup.style.display = "block";
    }
}

async function updateCameraSelector() {
    if (appConfig.demo_mode_active || isCloudMode) return;
    
    try {
        const res = await fetch("/api/cameras");
        if (res.ok) {
            const cameras = await res.json();
            const selectEl = document.getElementById("camera-select");
            selectEl.innerHTML = "";
            
            if (cameras.length === 0) {
                const opt = document.createElement("option");
                opt.value = "0";
                opt.innerText = "No Cameras Found";
                selectEl.appendChild(opt);
                return;
            }
            
            cameras.forEach(idx => {
                const opt = document.createElement("option");
                opt.value = idx;
                opt.innerText = `Camera Index ${idx}`;
                if (idx === appConfig.camera_index) opt.selected = true;
                selectEl.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Failed to query cameras list:", e);
    }
}

function updateSystemHealthDisplay() {
    // Engine label
    const engineEl = document.getElementById("status-engine");
    if (appConfig.inspection_mode === "PCB") {
        engineEl.innerText = "HYBRID CV SEGMENTER";
        engineEl.className = "health-value status-ok";
    } else {
        // If in Vercel Cloud, YOLO will fall back to CV mode gracefully
        engineEl.innerText = isCloudMode ? "CV CLASSIC MODE" : "YOLOv8 ENGINE (CPU)";
        engineEl.className = "health-value status-ok";
    }
    
    // Source label
    const sourceEl = document.getElementById("status-source");
    if (appConfig.demo_mode_active) {
        sourceEl.innerText = "STATIC DEMO";
        sourceEl.style.color = "var(--text-muted)";
    } else {
        sourceEl.innerText = isCloudMode ? "BROWSER WEBCAM (CLOUD)" : `PHYSICAL CAM (IDX ${appConfig.camera_index})`;
        sourceEl.style.color = "var(--color-primary)";
    }
}

// Config Post updates
async function saveConfig() {
    try {
        const response = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(appConfig)
        });
        if (response.ok) {
            const data = await response.json();
            appConfig = data.config;
            updateSystemHealthDisplay();
        }
    } catch (err) {
        console.error("Failed to save backend configuration:", err);
    }
}

function setupConfigListeners() {
    // Demo Mode toggle
    document.getElementById("demo-mode-toggle").addEventListener("change", (e) => {
        appConfig.demo_mode_active = e.target.checked;
        toggleCameraSelectVisibility(appConfig.demo_mode_active);
        if (!appConfig.demo_mode_active) {
            updateCameraSelector();
        }
        saveConfig();
        
        // Restart stream if active to switch feeds
        const streamToggle = document.getElementById("stream-toggle");
        if (streamToggle.checked) {
            restartStream();
        }
    });

    // Camera select change
    document.getElementById("camera-select").addEventListener("change", (e) => {
        appConfig.camera_index = parseInt(e.target.value);
        saveConfig();
        
        // Restart stream if active to switch index
        const streamToggle = document.getElementById("stream-toggle");
        if (streamToggle.checked) {
            restartStream();
        }
    });

    // Slider threshold change
    const thresholdSlider = document.getElementById("threshold-slider");
    thresholdSlider.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        document.getElementById("threshold-val").innerText = val.toFixed(1) + "%";
    });
    
    thresholdSlider.addEventListener("change", (e) => {
        appConfig.decision_threshold = parseFloat(e.target.value);
        saveConfig();
    });
}

// Scanner Screen Controller
function setupScannerListeners() {
    // Inspection mode Select
    document.getElementById("inspection-mode").addEventListener("change", (e) => {
        appConfig.inspection_mode = e.target.value;
        saveConfig();
    });

    // Override mode Select
    document.getElementById("override-select").addEventListener("change", (e) => {
        appConfig.demo_override = e.target.value;
        saveConfig();
    });

    // Stream toggle
    const streamToggle = document.getElementById("stream-toggle");
    streamToggle.addEventListener("change", (e) => {
        const streamActive = e.target.checked;
        handleStreamToggle(streamActive);
    });

    // Scan trigger button
    document.getElementById("trigger-scan-btn").addEventListener("click", () => {
        triggerQualityScan();
    });

    // On-demand PDF compiler event binding for active scanner Result Card
    document.getElementById("res-report-link").addEventListener("click", async (e) => {
        e.preventDefault();
        if (!lastScanResult) return;
        
        // If live webcam was scanning in browser cloud mode, extract base64 from canvas to embed in PDF
        let b64 = null;
        if (isCloudMode && !appConfig.demo_mode_active) {
            const canvas = document.getElementById("browser-canvas");
            b64 = canvas.toDataURL("image/jpeg");
        }
        
        await downloadPDFReport(lastScanResult, b64);
    });
}

// Helper to start/stop the browser-based camera feed (Cloud Vercel fallback)
async function handleStreamToggle(active) {
    const streamImg = document.getElementById("live-stream-img");
    const browserVideo = document.getElementById("browser-video");
    const standbyScreen = document.getElementById("standby-screen");
    const feedStatus = document.getElementById("feed-status-badge");
    
    if (active) {
        standbyScreen.style.display = "none";
        
        if (isCloudMode && !appConfig.demo_mode_active) {
            // Cloud Mode + Live WebCam: Request browser camera API stream
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { width: 640, height: 480, facingMode: "environment" } 
                });
                browserVideo.srcObject = stream;
                browserVideo.style.display = "block";
                streamImg.style.display = "none";
                
                feedStatus.innerHTML = '<span class="dot"></span> LIVE FEED (BROWSER)';
                feedStatus.className = "feed-status streaming";
            } catch (e) {
                console.error("Browser camera access denied:", e);
                alert("Camera access denied. Please grant webcam permissions in your browser configuration.");
                document.getElementById("stream-toggle").checked = false;
                standbyScreen.style.display = "flex";
                browserVideo.style.display = "none";
            }
        } else {
            // Local Mode or Demo Mode Fallback: Stream standard Python MJPEG or Cycle Demo
            browserVideo.style.display = "none";
            streamImg.style.display = "block";
            streamImg.src = `/api/video_feed?t=${Date.now()}`;
            
            feedStatus.innerHTML = '<span class="dot"></span> LIVE FEED';
            feedStatus.className = "feed-status streaming";
        }
    } else {
        // Shutdown feeds
        if (browserVideo.srcObject) {
            browserVideo.srcObject.getTracks().forEach(track => track.stop());
            browserVideo.srcObject = null;
        }
        
        browserVideo.style.display = "none";
        streamImg.src = "";
        streamImg.style.display = "none";
        standbyScreen.style.display = "flex";
        
        feedStatus.innerHTML = '<span class="dot"></span> STANDBY';
        feedStatus.className = "feed-status";
    }
}

function restartStream() {
    handleStreamToggle(false);
    setTimeout(() => {
        const streamToggle = document.getElementById("stream-toggle");
        if (streamToggle.checked) {
            handleStreamToggle(true);
        }
    }, 150);
}

// Snaps a browser camera frame and converts it to a JPEG base64 string
async function captureBrowserFrame() {
    const video = document.getElementById("browser-video");
    const canvas = document.getElementById("browser-canvas");
    
    if (video.srcObject && video.srcObject.active) {
        // Stream is running: draw current frame
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL("image/jpeg");
    }
    
    // Stream not running: open camera temporarily, snapshot, and close
    try {
        const tempStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480, facingMode: "environment" } 
        });
        const tempVideo = document.createElement("video");
        tempVideo.srcObject = tempStream;
        
        // Wait for video meta to initialize and play
        await new Promise((resolve) => {
            tempVideo.onloadedmetadata = () => {
                tempVideo.play().then(resolve);
            };
        });
        
        const ctx = canvas.getContext("2d");
        ctx.drawImage(tempVideo, 0, 0, canvas.width, canvas.height);
        
        // Stop stream
        tempStream.getTracks().forEach(track => track.stop());
        return canvas.toDataURL("image/jpeg");
    } catch (e) {
        console.error("Camera acquisition failed in browser:", e);
        return null;
    }
}

async function triggerQualityScan() {
    const scanBtn = document.getElementById("trigger-scan-btn");
    const originalText = scanBtn.innerHTML;
    
    scanBtn.disabled = true;
    scanBtn.innerHTML = '<i data-lucide="loader" class="animation-spin"></i> Running AI Engine...';
    lucide.createIcons();
    
    try {
        let payload = {};
        
        // If running in cloud Vercel environment AND not in demo mode: send browser camera capture
        if (isCloudMode && !appConfig.demo_mode_active) {
            const base64Img = await captureBrowserFrame();
            if (!base64Img) {
                alert("Camera scan failed. Please verify that webcam permissions are enabled.");
                return;
            }
            payload.image = base64Img;
        }
        
        const res = await fetch("/api/scan", { 
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: Object.keys(payload).length > 0 ? JSON.stringify(payload) : null
        });
        
        if (res.ok) {
            const data = await res.json();
            lastScanResult = data; // Keep metadata reference for dynamic PDF compilation
            renderInspectionResult(data);
            
            // If continuous feed is OFF, we display the returned inspection crop on the dashboard viewport
            const streamToggle = document.getElementById("stream-toggle");
            if (!streamToggle.checked) {
                const streamImg = document.getElementById("live-stream-img");
                const standbyScreen = document.getElementById("standby-screen");
                standbyScreen.style.display = "none";
                streamImg.style.display = "block";
                streamImg.src = `${data.image_path}?t=${Date.now()}`;
            }
            
            // Dynamic dashboard updates
            updateAnalytics();
            updateHistory();
        } else {
            alert("Visual Scan trigger failed. Please check local terminal logs.");
        }
    } catch (e) {
        console.error("Scanning request failed:", e);
        alert("Server failed to respond to quality inspection trigger.");
    } finally {
        scanBtn.disabled = false;
        scanBtn.innerHTML = originalText;
        lucide.createIcons();
    }
}

function renderInspectionResult(data) {
    document.getElementById("result-placeholder").style.display = "none";
    document.getElementById("result-details").style.display = "block";
    
    const badge = document.getElementById("res-badge");
    const badgeText = document.getElementById("res-badge-text");
    badgeText.innerText = data.result;
    
    if (data.result === "PASS") {
        badge.className = "result-badge pass";
    } else {
        badge.className = "result-badge fail";
    }
    
    document.getElementById("res-product-id").innerText = data.product_id;
    document.getElementById("res-confidence").innerText = data.confidence.toFixed(1) + "%";
    document.getElementById("res-confidence-bar").style.width = data.confidence + "%";
    
    document.getElementById("res-timestamp").innerText = data.timestamp;
    document.getElementById("res-record-id").innerText = `#${data.id}`;
    
    const defectCard = document.getElementById("res-defect-card");
    const defectDesc = document.getElementById("res-defect-desc");
    
    if (data.defect_type) {
        defectCard.style.display = "block";
        
        if (data.defect_type === "Missing Component") {
            defectDesc.innerText = "Check component chip reels. The targeted outline contains fewer component boundaries than expected (3 bodies target).";
        } else if (data.defect_type === "Component Misalignment") {
            defectDesc.innerText = "Check assembly guides. One or more component IC packages exceed angular skew tolerance parameters (12 degrees offset check).";
        } else {
            defectDesc.innerText = `Visual anomaly alert flagged: ${data.defect_type}`;
        }
    } else {
        defectCard.style.display = "none";
    }
}

// Dynamic, stateless PDF report downloader
async function downloadPDFReport(recordData, base64Image = null) {
    try {
        const payload = {
            id: recordData.id,
            timestamp: recordData.timestamp,
            product_id: recordData.product_id,
            result: recordData.result,
            defect_type: recordData.defect_type,
            confidence: recordData.confidence,
            image_path: recordData.image_path,
            image_b64: base64Image
        };
        
        const response = await fetch("/api/reports/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `VisionGuard_Report_${recordData.product_id}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert("Vercel serverless report generation failed.");
        }
    } catch (e) {
        console.error("PDF download request failed:", e);
        alert("Failed to communicate with Vercel PDF generation API.");
    }
}

// Analytics and Charts Dashboard Section
async function updateAnalytics() {
    try {
        const response = await fetch("/api/analytics");
        if (!response.ok) return;
        
        const stats = await response.json();
        
        document.getElementById("stat-total").innerText = stats.total.toLocaleString();
        document.getElementById("stat-passed").innerText = stats.passed.toLocaleString();
        document.getElementById("stat-failed").innerText = stats.failed.toLocaleString();
        document.getElementById("stat-yield").innerText = stats.pass_rate.toFixed(2) + "%";
        
        document.getElementById("diag-config-threshold").innerText = appConfig.decision_threshold.toFixed(1) + "%";
        
        const statusBadge = document.getElementById("yield-status-badge");
        if (stats.pass_rate >= 90.0) {
            statusBadge.innerText = "PASSING";
            statusBadge.className = "status-badge";
        } else {
            statusBadge.innerText = "CHECK LINE";
            statusBadge.className = "status-badge failing";
        }
        
        document.getElementById("gauge-fill").style.width = stats.pass_rate + "%";
        document.getElementById("gauge-caption").innerText = `Yield conforms to target MSME quality specifications.`;
        
        renderDefectChart(stats.defect_distribution);
    } catch (e) {
        console.error("Failed to load yield analytics summary:", e);
    }
}

function renderDefectChart(distribution) {
    const ctx = document.getElementById("defectChart").getContext("2d");
    const labels = Object.keys(distribution);
    const data = Object.values(distribution);
    
    if (defectChartInstance !== null) {
        defectChartInstance.data.labels = labels;
        defectChartInstance.data.datasets[0].data = data;
        defectChartInstance.update();
    } else {
        defectChartInstance = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Incident Quantity",
                    data: data,
                    backgroundColor: "rgba(59, 130, 246, 0.4)",
                    borderColor: "rgba(59, 130, 246, 1)",
                    borderWidth: 1.5,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#94a3b8" }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: "#94a3b8" }
                    }
                }
            }
        });
    }
}

function setupDashboardListeners() {
    document.getElementById("reset-db-btn").addEventListener("click", async () => {
        if (confirm("Are you sure you want to restore the SQLite database? This will clear all current records and load 120 mock demo items.")) {
            try {
                const response = await fetch("/api/reset_db", { method: "POST" });
                if (response.ok) {
                    alert("Database successfully reset!");
                    updateAnalytics();
                    updateHistory();
                }
            } catch (err) {
                console.error("DB reset error:", err);
            }
        }
    });
}

// Logs Table Screen
async function updateHistory() {
    try {
        const response = await fetch("/api/history");
        if (!response.ok) return;
        
        currentHistoryData = await response.json();
        renderHistoryTable(currentHistoryData);
        
        const searchInput = document.getElementById("log-search-input");
        searchInput.removeEventListener("input", filterHistoryLogs);
        searchInput.addEventListener("input", filterHistoryLogs);
    } catch (e) {
        console.error("Failed to load visual inspection logs history:", e);
    }
}

function renderHistoryTable(dataList) {
    const tableBody = document.getElementById("history-table-body");
    tableBody.innerHTML = "";
    
    if (dataList.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No records found in quality archive files.</td></tr>';
        return;
    }
    
    dataList.forEach(row => {
        const tr = document.createElement("tr");
        tr.setAttribute("data-row-id", row.id);
        
        const badgeClass = row.result === "PASS" ? "badge-sm pass" : "badge-sm fail";
        const defectText = row.defect_type ? row.defect_type : "—";
        
        tr.innerHTML = `
            <td>#${row.id}</td>
            <td>${row.timestamp}</td>
            <td class="font-mono" style="font-weight: 600;">${row.product_id}</td>
            <td><span class="${badgeClass}">${row.result}</span></td>
            <td>${defectText}</td>
            <td class="font-mono">${row.confidence.toFixed(1)}%</td>
        `;
        
        tr.addEventListener("click", () => {
            selectHistoryRow(row.id, tr);
        });
        
        tableBody.appendChild(tr);
    });
}

function filterHistoryLogs() {
    const query = document.getElementById("log-search-input").value.trim().toLowerCase();
    if (!query) {
        renderHistoryTable(currentHistoryData);
        return;
    }
    
    const filtered = currentHistoryData.filter(item => 
        item.product_id.toLowerCase().includes(query) ||
        (item.defect_type && item.defect_type.toLowerCase().includes(query))
    );
    
    renderHistoryTable(filtered);
}

function selectHistoryRow(id, element) {
    document.querySelectorAll("#history-table-body tr").forEach(tr => {
        tr.classList.remove("selected");
    });
    
    element.classList.add("selected");
    
    const record = currentHistoryData.find(item => item.id === id);
    if (!record) return;
    
    document.getElementById("detail-placeholder").style.display = "none";
    document.getElementById("detail-content").style.display = "flex";
    
    document.getElementById("detail-run-title").innerText = `Inspection Run #${record.id}`;
    
    const badge = document.getElementById("detail-result-badge");
    badge.innerText = record.result;
    if (record.result === "PASS") {
        badge.className = "detail-badge pass";
    } else {
        badge.className = "detail-badge fail";
    }
    
    document.getElementById("detail-timestamp").innerText = record.timestamp;
    document.getElementById("detail-product-id").innerText = record.product_id;
    document.getElementById("detail-defect").innerText = record.defect_type ? record.defect_type : "None";
    document.getElementById("detail-confidence").innerText = record.confidence.toFixed(1) + "%";
    document.getElementById("detail-model").innerText = record.model_version;
    
    const imgEl = document.getElementById("detail-img");
    if (record.image_path) {
        imgEl.src = record.image_path + `?t=${Date.now()}`;
    } else {
        imgEl.src = "";
    }
    
    // Bind dynamic PDF compiler event listener to logs Detail Panel download link
    const pdfLink = document.getElementById("detail-report-link");
    pdfLink.onclick = async (e) => {
        e.preventDefault();
        await downloadPDFReport(record, null);
    };
}
