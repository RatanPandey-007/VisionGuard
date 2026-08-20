import cv2
import numpy as np
import os

def create_pcb_template(bg_color=(35, 120, 35)):
    """Creates a base green PCB board image."""
    # 640x480 frame, with a grey workbench background
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
    
    # Draw green PCB board in the center
    # Board is 380x280 centered
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
    """Draws a rotated rectangular chip components with silver pins onto the image."""
    # Generate rectangle points
    rect = (center, size, angle)
    box = cv2.boxPoints(rect)
    box = np.intp(box)
    
    # Fill body
    cv2.drawContours(img, [box], 0, color, -1)
    
    # Draw pins along left/right edge
    # We find coordinates along the box segment vectors
    # Simplified approach: Draw pin indicators using rotating math
    theta = np.deg2rad(angle)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    
    cx, cy = center
    w, h = size
    
    # Pins spacing (5 pins on each long side)
    side_length = max(w, h)
    for offset in np.linspace(-side_length/2 + 5, side_length/2 - 5, 5):
        # Calculate offset coordinate
        if w > h:
            # Pins along horizontal sides
            px1 = cx + offset * cos_t - (h/2 + 3) * sin_t
            py1 = cy + offset * sin_t + (h/2 + 3) * cos_t
            px2 = cx + offset * cos_t + (h/2 + 3) * sin_t
            py2 = cy + offset * sin_t - (h/2 + 3) * cos_t
        else:
            # Pins along vertical sides
            px1 = cx - (w/2 + 3) * cos_t + offset * sin_t
            py1 = cy - (w/2 + 3) * sin_t - offset * cos_t
            px2 = cx + (w/2 + 3) * cos_t + offset * sin_t
            py2 = cy + (w/2 + 3) * sin_t - offset * cos_t
            
        cv2.circle(img, (int(px1), int(py1)), 2, (200, 200, 200), -1)
        cv2.circle(img, (int(px2), int(py2)), 2, (200, 200, 200), -1)

def save_sample_pcbs():
    demo_dir = os.path.join("data", "demo_samples")
    os.makedirs(demo_dir, exist_ok=True)
    
    # 1. Good PCB 1 (Straight component chips)
    pcb_good1 = create_pcb_template()
    draw_chip(pcb_good1, (230, 200), (35, 60), 0)
    draw_chip(pcb_good1, (410, 200), (35, 60), 0)
    draw_chip(pcb_good1, (320, 290), (60, 35), 0)
    cv2.imwrite(os.path.join(demo_dir, "01_perfect_pcb_a.png"), pcb_good1)
    
    # 2. Good PCB 2 (Straight chips, slightly different positions)
    pcb_good2 = create_pcb_template((45, 110, 45))
    draw_chip(pcb_good2, (230, 200), (35, 60), 0)
    draw_chip(pcb_good2, (410, 200), (35, 60), 0)
    draw_chip(pcb_good2, (320, 290), (60, 35), 0)
    cv2.imwrite(os.path.join(demo_dir, "02_perfect_pcb_b.png"), pcb_good2)
    
    # 3. Defective PCB - Missing component (Third chip is not drawn)
    pcb_missing = create_pcb_template()
    draw_chip(pcb_missing, (230, 200), (35, 60), 0)
    draw_chip(pcb_missing, (410, 200), (35, 60), 0)
    # Draw exposed tin pad outline (two silver boxes where chip 3 should sit)
    cv2.rectangle(pcb_missing, (290, 275), (350, 305), (180, 180, 180), 1)
    cv2.imwrite(os.path.join(demo_dir, "03_defect_missing_chip.png"), pcb_missing)
    
    # 4. Defective PCB - Misaligned Component (Third chip is rotated 25 degrees)
    pcb_misaligned = create_pcb_template()
    draw_chip(pcb_misaligned, (230, 200), (35, 60), 0)
    draw_chip(pcb_misaligned, (410, 200), (35, 60), 0)
    draw_chip(pcb_misaligned, (320, 290), (60, 35), 25) # 25 degree offset!
    cv2.imwrite(os.path.join(demo_dir, "04_defect_misaligned_chip.png"), pcb_misaligned)
    
    print(f"Sample PCB dataset generated successfully inside: {demo_dir}")

if __name__ == "__main__":
    save_sample_pcbs()
