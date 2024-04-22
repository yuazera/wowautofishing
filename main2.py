import threading
from array import array
import queue 
from queue import Queue, Full
import pyaudio
import time
import cv2
import mss
import numpy as np
import pyautogui
import win32gui
import pygetwindow as gw


CHUNK_SIZE = 1024
MIN_VOLUME = 50
# if the recording thread can't consume fast enough, the listener will start discarding
BUF_MAX_SIZE = CHUNK_SIZE * 10

handle = None

while True:
    # 获取当前活动窗口
    hwnd = win32gui.GetForegroundWindow()
    # 获取窗口的标题
    title = win32gui.GetWindowText(hwnd)

    # 如果标题为"魔兽世界"，则保存句柄，并结束循环
    if title == "魔兽世界":
        handle = hwnd
        print(f"找到了魔兽世界！句柄是：{handle}")
        break

    # 暂停一会，避免过多占用CPU
    time.sleep(0.1)

game_window_rect = win32gui.GetWindowRect(handle)  # left, top, right, bottom

# Crop game client down to fishing area to reduce false positives

lock = threading.Lock()

def main():
    stopped = threading.Event()
    q = Queue(maxsize=int(round(BUF_MAX_SIZE / CHUNK_SIZE)))
    
    # 创建 add_yuer 线程，并将锁传递给它
    add_yuer_t = threading.Thread(target=add_yuer, args=(stopped, lock))
    # 启动 add_yuer 线程
    add_yuer_t.start()
    listen_t = threading.Thread(target=listen, args=(stopped, q))
    listen_t.start()
    record_t = threading.Thread(target=record, args=(stopped, q))
    record_t.start()

    try:
        while True:
            # listen_t.join(0.1)
            record_t.join(0.1)
    except KeyboardInterrupt:
        stopped.set()

    listen_t.join()
    record_t.join()

def get_click_point(target):
    # capture the positon of the float
    points = []
    for _ in range(19):
        with  mss.mss() as sct:
            monitor = {"top": game_window_rect[1], "left": game_window_rect[0], "width": game_window_rect[2] - game_window_rect[0], "height": game_window_rect[3] - game_window_rect[1]}
            # 保存顶部和右边修剪前的位置信息
            original_top = monitor['top']
            original_left = monitor['left']
            # 从顶部去掉1/5的高度
            monitor['top'] += monitor['height'] // 5
            monitor['height'] -= monitor['height'] // 5

            # 从右边去掉1/10的宽度
            monitor['width'] -= monitor['width'] // 10
            #print("Updated monitor area:", monitor)
            time.sleep(0.1)
            img_rgb = np.array(sct.grab(monitor))
            
            #预览截图
            #cv2.imshow('Detected', img_rgb)
            #cv2.waitKey(0)
            #cv2.destroyAllWindows()
            
            
            img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
            gaussian_blur = cv2.GaussianBlur(img_gray, (5, 5), 0)
            adaptive_thresh = cv2.adaptiveThreshold(gaussian_blur, 255, 
                                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)
            img_eq = cv2.equalizeHist(adaptive_thresh)
            template = cv2.imread(target,0)
            template_blur = cv2.GaussianBlur(template, (5, 5), 0)
#            temp_adaptive_thresh = cv2.adaptiveThreshold(template_blur, 255, 
#                                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
#                                        cv2.THRESH_BINARY, 11, 2)
                                        
            template_eq = cv2.equalizeHist(template_blur)
            
            w, h = template.shape[::-1]

            res = cv2.matchTemplate(img_eq,template_eq,cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            top_left = (max_loc[0] + original_left, max_loc[1] + original_top + monitor['height'] // 5)
#            top_left = max_loc
#            bottom_right = (top_left[0] + w, top_left[1] + h)


#           调整bottom_right坐标，使其宽度为原宽度的2/3
            bottom_right = (top_left[0] + (3 * w // 4), top_left[1] + (4 * h // 3))
            
            click_point = ((bottom_right[0] + top_left[0])/2, (bottom_right[1]+top_left[1])/2)
            points.append(click_point)
            # debug_img(img_rgb, top_left, bottom_right)
    points.sort(key=lambda tup:tup[0])
    return points[10]

def debug_img(img_rgb, top_left, bottom_right):
    cv2.rectangle(img_rgb, top_left, bottom_right, (0,0,255), 2)
    cv2.imwrite("debug.png", img_rgb)

def add_yuer(stopped, lock):
    while not stopped.is_set():
        # 获取锁
        with lock:
            pyautogui.press('8')
            # 持锁状态执行8秒钟
            time.sleep(8)
        # 释放锁后休眠292秒（总周期300秒）
        time.sleep(292)
    
    
def start_fishing(lock):
    # 通过lock获取锁来同步线程
    with lock:
        # 如果获得锁，执行这里的代码
        pyautogui.press('3')
        time.sleep(4)

def click_the_bait(click_point):
    print(click_point)
    pyautogui.moveTo(click_point[0], click_point[1], 0.5, pyautogui.easeInOutQuad)
    time.sleep(300/1000)
    pyautogui.click(button="right")
    
def click_the_bait_bite(click_point):
    print(click_point)
    pyautogui.moveTo(click_point[0], click_point[1], 0.1, pyautogui.easeInOutQuad)
#    time.sleep(300/1000)
    pyautogui.click(button="right")    

def record(stopped, q):
    is_fishing = False
    thresh_reach_count = 0
    start_fishing_time = time.time()
    max_inactive_sound_gap = 0
    start_time = time.time()
    # give some time to switch window focus
    time.sleep(1)
    while True:
        if stopped.wait(timeout=0):
            break
        # 清空队列以确保获得最新的音频数据
        while not q.empty():
            chunk = q.get()
            vol = max(chunk)
            if vol < 15:
                break  # 如果vol为1，跳出循环，开始处理这个音频块

        # auto get bait buff
        # if time.time()-start_time>60*10:
        #     click_point = get_click_point('bait.png')
        #     click_the_bait(click_point)
        #     time.sleep(6)
        #     start_time = time.time()
        # timeout after 30s, restart everything
        if time.time() - start_fishing_time > 34:
            is_fishing = False
            thresh_reach_count = 0
            start_fishing_time = time.time()
        if not is_fishing:
            print("Start fishing")
            start_fishing(lock)
            time.sleep(2)
            click_point = get_click_point('float5.png')
            pyautogui.moveTo(click_point[0], click_point[1], 1, pyautogui.easeInOutQuad)
            is_fishing = True
        chunk = q.get()
        vol = max(chunk)
        print(vol)
        if vol >= MIN_VOLUME:
            # ignore the first fishing sound
            if time.time() - start_fishing_time > 10:
                thresh_reach_count = thresh_reach_count+1
                max_inactive_sound_gap = 0
                print("O"),
#        else:
            # only clears thresh after more than 15 no sound frame
#            if max_inactive_sound_gap > 2048:
 #               thresh_reach_count = 0
            # print("-")
#            max_inactive_sound_gap = max_inactive_sound_gap + 1
        if thresh_reach_count>1:
            print("Clicking bait")
            click_the_bait_bite(click_point)
            time.sleep(1)
            is_fishing = False
            thresh_reach_count = 0
            start_fishing_time = time.time()


def listen(stopped, q):
    stream = pyaudio.PyAudio().open(
        format=pyaudio.paInt16,
        channels=2,
        rate=44100,
        input=True,
        frames_per_buffer=1024,
    )

    while True:
        if stopped.wait(timeout=0):
            break
        try:
            q.put(array('h', stream.read(CHUNK_SIZE)))
        except Full:
            pass  # discard


if __name__ == '__main__':
    main()
