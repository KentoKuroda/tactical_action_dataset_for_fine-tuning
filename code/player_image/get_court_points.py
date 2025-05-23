import argparse
import cv2

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', required=True)
    return parser.parse_args()


def main():
    args = parse_arguments()
    video_path = args.video
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Cannot open video")
        return
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Error: Cannot read frame 100")
        return
    
    cv2.imshow("Frame 100", frame)
    cv2.setMouseCallback("Frame 100", click_event)
    
    print("Press Enter to exit")
    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == 13:  # Enter key
            break
    
    cv2.destroyAllWindows()


def click_event(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Clicked position: ({x}, {y})")


if __name__ == '__main__':
    main()
