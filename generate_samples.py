import cv2
import numpy as np
import os

def create_pcb_template(bg_color=(35, 120, 35)):
    """Creates a base green PCB board image."""
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 40 # Dark gray workbench
    
    # Draw green PCB board in the center (380x280 centered)
    cv2.rectangle(frame, (130, 100), (510, 380), bg_color, -1)
    
    # Draw copper corner mounts
    centers = [(150, 120), (490, 120), (150, 360), (490, 360)]
    for pt in centers:
        cv2.circle(frame, pt, 8, (120, 200, 220), -1)
        cv2.circle(frame, pt, 4, (60, 60, 60), -1)
        
    # Draw traces (gold circuit lines)
    cv2.line(frame, (170, 150), (470, 150), (30, 190, 210), 2)
    cv2.line(frame, (170, 240), (470, 240), (30, 190, 210), 2)
    cv2.line(frame, (170, 330), (470, 330), (30, 190, 210), 2)
    cv2.line(frame, (230, 150), (230, 330), (30, 190, 210), 1)
    cv2.line(frame, (410, 150), (410, 330), (30, 190, 210), 1)
    
    return frame

def draw_chip(img, center, size, angle, color=(30, 30, 30)):
    """Draws a rotated rectangular chip component with silver pins."""
    rect = (center, size, angle)
    box = cv2.boxPoints(rect)
    box = np.intp(box)
    
    cv2.drawContours(img, [box], 0, color, -1)
    
    # Draw pins along edges
    theta = np.deg2rad(angle)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    
    cx, cy = center
    w, h = size
    
    side_length = max(w, h)
    for offset in np.linspace(-side_length/2 + 5, side_length/2 - 5, 5):
        if w > h:
            px1 = cx + offset * cos_t - (h/2 + 3) * sin_t
            py1 = cy + offset * sin_t + (h/2 + 3) * cos_t
            px2 = cx + offset * cos_t + (h/2 + 3) * sin_t
            py2 = cy + offset * sin_t - (h/2 + 3) * cos_t
        else:
            px1 = cx - (w/2 + 3) * cos_t + offset * sin_t
            py1 = cy - (w/2 + 3) * sin_t - offset * cos_t
            px2 = cx + (w/2 + 3) * cos_t + offset * sin_t
            py2 = cy + (w/2 + 3) * sin_t - offset * cos_t
            
        cv2.circle(img, (int(px1), int(py1)), 2, (200, 200, 200), -1)
        cv2.circle(img, (int(px2), int(py2)), 2, (200, 200, 200), -1)

# --- Gear Generator ---
def create_gear_template(radius=100, inner_radius=30, teeth_count=12, teeth_height=15, defect=None, bg_color=(200, 190, 180)):
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 35 # Dark gray bench
    cx, cy = 320, 240
    
    # 1. Draw outer gear profile with teeth
    points = []
    for i in range(teeth_count * 2):
        angle = i * (2 * np.pi / (teeth_count * 2))
        # Alternate radius to create teeth valleys and peaks
        r = radius if i % 2 == 0 else (radius + teeth_height)
        
        # Add slight size variation if dimension defect is triggered
        if defect == "dimension" and i % 2 == 0:
            r -= 25 # Shrink size noticeably
            
        px = int(cx + r * np.cos(angle))
        py = int(cy + r * np.sin(angle))
        points.append((px, py))
        
    pts = np.array(points, dtype=np.int32)
    
    # Draw gear base
    cv2.fillPoly(frame, [pts], bg_color)
    cv2.polylines(frame, [pts], True, (60, 60, 60), 2)
    
    # Draw inner circle metal highlights
    cv2.circle(frame, (cx, cy), int(radius * 0.7), (220, 210, 200), 1)
    
    # 2. Draw shaft center hole
    cv2.circle(frame, (cx, cy), inner_radius, (10, 10, 10), -1)
    cv2.circle(frame, (cx, cy), inner_radius, (90, 90, 90), 2)
    
    # 3. Draw defects
    if defect == "crack":
        # Draw a structural fracture crack radiating from center hole to outer edge
        cv2.line(frame, (cx + 10, cy - 28), (cx + 45, cy - 100), (10, 10, 10), 3)
        cv2.line(frame, (cx + 12, cy - 26), (cx + 42, cy - 98), (0, 0, 255), 1) # Red highlight for OpenCV crack detection
        
    return frame

# --- Blister Pack Pills Generator ---
def create_pills_template(missing_idx=None, bg_color=(235, 235, 235)):
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 35 # Dark gray workbench
    
    # Draw blister cardboard backing (300x200 centered)
    cv2.rectangle(frame, (170, 140), (470, 340), bg_color, -1)
    cv2.rectangle(frame, (170, 140), (470, 340), (180, 180, 180), 2)
    
    # Draw grid of 6 pockets (3x2)
    # Positions of pocket centers
    cols = [220, 320, 420]
    rows = [190, 290]
    
    idx = 0
    for r in rows:
        for c in cols:
            # Draw pocket boundary (silver shadow)
            cv2.ellipse(frame, (c, r), (35, 25), 0, 0, 360, (200, 200, 200), -1)
            cv2.ellipse(frame, (c, r), (35, 25), 0, 0, 360, (140, 140, 140), 1)
            
            # Draw pill if not flagged missing
            if missing_idx != idx:
                # Capsules: half red, half blue
                # Draw left half (blue)
                cv2.rectangle(frame, (c - 20, r - 8), (c, r + 8), (180, 50, 50), -1) # Blue in BGR
                # Draw right half (red)
                cv2.rectangle(frame, (c, r - 8), (c + 20, r + 8), (50, 50, 200), -1) # Red in BGR
                # Draw white outline/band
                cv2.rectangle(frame, (c - 20, r - 8), (c + 20, r + 8), (255, 255, 255), 1)
                cv2.circle(frame, (c - 20, r), 8, (180, 50, 50), -1)
                cv2.circle(frame, (c + 20, r), 8, (50, 50, 200), -1)
            else:
                # Missing: Draw empty foil tear outline
                cv2.ellipse(frame, (c, r), (20, 10), 0, 0, 360, (100, 100, 10), 1)
                
            idx += 1
            
    return frame

def save_all_samples():
    demo_dir = os.path.join("data", "demo_samples")
    static_dir = os.path.join("static", "mock_images")
    os.makedirs(demo_dir, exist_ok=True)
    os.makedirs(static_dir, exist_ok=True)
    
    # 1. Good PCB 1 (Straight component chips)
    pcb_good1 = create_pcb_template()
    draw_chip(pcb_good1, (230, 200), (35, 60), 0)
    draw_chip(pcb_good1, (410, 200), (35, 60), 0)
    draw_chip(pcb_good1, (320, 290), (60, 35), 0)
    
    # 2. Defective PCB - Missing component
    pcb_missing = create_pcb_template()
    draw_chip(pcb_missing, (230, 200), (35, 60), 0)
    draw_chip(pcb_missing, (410, 200), (35, 60), 0)
    cv2.rectangle(pcb_missing, (290, 275), (350, 305), (180, 180, 180), 1)
    
    # 3. Defective PCB - Misaligned Component
    pcb_misaligned = create_pcb_template()
    draw_chip(pcb_misaligned, (230, 200), (35, 60), 0)
    draw_chip(pcb_misaligned, (410, 200), (35, 60), 0)
    draw_chip(pcb_misaligned, (320, 290), (60, 35), 25)
    
    # 4. Gears
    gear_good = create_gear_template()
    gear_bad_crack = create_gear_template(defect="crack")
    gear_bad_size = create_gear_template(defect="dimension")
    
    # 5. Blister Pills
    pills_good = create_pills_template()
    pills_bad = create_pills_template(missing_idx=3)
    
    # Write to local demo and static directories
    images = {
        "01_perfect_pcb_a.png": pcb_good1,
        "03_defect_missing_chip.png": pcb_missing,
        "04_defect_misaligned_chip.png": pcb_misaligned,
        "05_perfect_gear.png": gear_good,
        "06_defect_gear_crack.png": gear_bad_crack,
        "07_defect_gear_dimension.png": gear_bad_size,
        "08_perfect_pills.png": pills_good,
        "09_defect_pills_missing.png": pills_bad
    }
    
    for filename, img in images.items():
        cv2.imwrite(os.path.join(demo_dir, filename), img)
        cv2.imwrite(os.path.join(static_dir, filename), img)
        
    print(f"Generated {len(images)} advanced mock samples successfully!")

if __name__ == "__main__":
    save_all_samples()
