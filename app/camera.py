import cv2
import time
import os
import glob
import numpy as np

class CameraInterface:
    """Base interface for image acquisition (Webcam, USB, or Demo Mock)"""
    def get_frame(self) -> tuple[bool, np.ndarray | None]:
        raise NotImplementedError("Each camera source must implement get_frame")
        
    def release(self):
        raise NotImplementedError("Each camera source must implement release")

class WebcamCamera(CameraInterface):
    """Acquires live video frames from a connected system camera using OpenCV."""
    def __init__(self, index=0):
        self.index = index
        # On Windows, CAP_DSHOW is generally much faster to init
        if os.name == 'nt':
            self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(self.index)
            
        # Default lower-resolution setup suitable for edge inference
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Reduce latency

    def get_frame(self) -> tuple[bool, np.ndarray | None]:
        if not self.cap or not self.cap.isOpened():
            if os.name == 'nt':
                self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            else:
                self.cap = cv2.VideoCapture(self.index)
            if not self.cap.isOpened():
                return False, None
                
        ret, frame = self.cap.read()
        if ret and frame is not None:
            return True, frame
        return False, None

    def release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()

class DemoImageCamera(CameraInterface):
    """Cycles through real pre-selected/demo PCB images for stable pitch demonstrations."""
    def __init__(self, demo_dir="data/demo_samples", loop=True):
        self.demo_dir = demo_dir
        self.loop = loop
        self.image_paths = []
        
        # Load jpg, png, jpeg matches
        if os.path.exists(demo_dir):
            for ext in ('*.jpg', '*.png', '*.jpeg'):
                self.image_paths.extend(glob.glob(os.path.join(demo_dir, ext)))
                self.image_paths.extend(glob.glob(os.path.join(demo_dir, ext.upper())))
                
        self.image_paths = sorted(self.image_paths)
        self.idx = 0

    def get_frame(self) -> tuple[bool, np.ndarray | None]:
        # Simulate slight camera hardware latency (100ms)
        time.sleep(0.1)
        
        if not self.image_paths:
            # Generate a dynamic fallback frame if no files exist
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Add dynamic grid pattern for context
            for y in range(0, 480, 40):
                cv2.line(frame, (0, y), (640, y), (40, 40, 40), 1)
            for x in range(0, 640, 40):
                cv2.line(frame, (x, 0), (x, 480), (40, 40, 40), 1)
                
            cv2.putText(frame, "VISIONGUARD EDGE - DEMO MODE", (50, 180), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, "Add images to data/demo_samples/ directory", (50, 220), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
            # Dynamic blinking indicator
            color = (0, 255, 0) if int(time.time()) % 2 == 0 else (0, 0, 255)
            cv2.circle(frame, (320, 300), 30, color, -1)
            cv2.putText(frame, "STATUS: STANDBY", (250, 360), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            return True, frame
            
        path = self.image_paths[self.idx % len(self.image_paths)]
        if self.loop or self.idx < len(self.image_paths):
            self.idx += 1
            
        if os.path.exists(path):
            frame = cv2.imread(path)
            if frame is not None:
                return True, frame
        return False, None

    def release(self):
        pass

def get_available_cameras(max_to_test=5) -> list[int]:
    """Helper to discover valid hardware camera indices on the host system."""
    available = []
    # Test indices fast
    for i in range(max_to_test):
        if os.name == 'nt':
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(i)
            
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(i)
            cap.release()
    return available

if __name__ == "__main__":
    print("Discovering active cameras...")
    cams = get_available_cameras()
    print(f"Available camera indices: {cams}")
    
    if cams:
        print("Testing camera 0 capture. Press Q to exit.")
        cam = WebcamCamera(cams[0])
        while True:
            ret, frame = cam.get_frame()
            if ret and frame is not None:
                cv2.imshow("VisionGuard Camera Test", frame)
            else:
                print("Failed to grab frame.")
                break
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cam.release()
        cv2.destroyAllWindows()
    else:
        print("No hardware cameras detected. Active fallback only.")
