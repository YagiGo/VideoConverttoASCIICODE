import sys
import os
import time
import threading
import termios
import tty
import cv2
import pyprind
class CharFrame:
    ascii_char = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\m^`'."

    def pixelToChar(self, luminance):
        return self.ascii_char[int(luminance/256 * len(self.ascii_char))]

    def convert(self, img, limitSize = -1, fill = False, wrap = False):
        if limitSize != -1 and (img.shape[0] > limitSize[1]) or (img.shape[1] > limitSize[0]): #对图像尺寸进行规范
            img = cv2.resize(img, limitSize, interpolation = cv2.INTER_AREA)
        ascii_frame = ''
        blank = ''
        if fill:
            blank += ' ' * (limitSize[0] - img.shape[1]) #填补空白

        if wrap:  #换行
            blank += '\n'
        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                ascii_frame += self.pixelToChar(img[i,j]) #转换至ASCII帧
            ascii_frame += blank
        return ascii_frame
class I2Char(CharFrame):
    result = None

    def __init__(self, path, limitSize = -1, fill = False, wrap = False,):
        self.getCharIamge(path, limitSize, fill, wrap)
    def getChargeImage(self, path, limitSize = -1, fill = False, wrap = False):
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return
        self.result = self.covert(img, limitSize, fill, wrap)

    def show(self, stream = 2):
        if self.result is None:
            return
        if stream == 1 and os.isatty(sys.stdout.fileno()):
            self.streamOut = sys.stdout.write
            self.streamFlush = sys.stdout.flush

        if stream == 2 and os.isatty(sys.stderr.fileno()):
            self.streamOut = sys.stderr.write
            self.streamFlush = sys.stderr.flush

        elif hasattr(stream, 'write'):
            self.streamOut = stream.write
            self.streamFlush = stream.flush
        self.streamOut(self.result)
        self.streamFlush()
        self.streamOut('\n')
class V2Char(CharFrame):
    charVideo = []
    timeInterval = 0.033 #存放播放时间间隔，用来让之后播放字符动画的帧率与原视频相同

    def __init__(self, path):
        if path.endwith('txt'):
            self.load(path) #直接打开转换好的文本文件
            return
        else:
            self.getCharVideo(path)
    def getCharVideo(self, filepath):
        self.charVideo = []
        cap = cv2.VideoCapture(filepath) #使用cv2.VideoCapture获取视频文件赋值给cap
        #cap.get() 方法我们可以获得视频的属性信息，比如 cap.get(3) 和 cap.get(4) 分别返回视频的宽高信息，
        # cap.get(5) 则返回视频的帧率，cap.get(7) 返回视频的总帧数。
        self.timeInterval = round(1/cap.get(5), 3)
        nf = int(cap.get(7)) #视频的总帧数
        print("Processing... Please Wait :)")
        for i in pyprind.prog_bar(range(nf)):  #pyprind。prog_bar用于生产进度条
            rawFrame = cv2.cvtColor(cap.read()[1], cv2.COLOR_BGR2GRAY) #cap.read() 读取视频的下一帧，
            # 其返回一个两元素的元组，第一个元素为 bool 值，指示帧是否被正确读取，第二个元素为 numpy.ndarray ，其存放的便是帧的数据
            #cv2.cvtColor转换图像的色彩空间，第一个为图像对象，第二个为转换类型，这里是彩色转灰度。
            frame = self.convert(rawFrame, os.get_terminal_size(), fill = True)
            self.charVideo.append(frame) #处理好的放在charVideo数组内
        cap.release() #释放release
    def export(self, filepath):
        if not self.charVideo:
            return
        with open(filepath, 'w') as f:
            for frame in self.charVideo:
                # 每一帧之后加一个换行符，一行就为一帧
                f.write(frame + '\n')
    def load(self, filepath):
        self.charVideo = []
        for i in open(filepath):
            self.charVideo.append(i[:-1])
    def play(self, stream = 1):
        if not self.charVideo:
            return
        if stream == 1 and os.isatty(sys.stdout.fileno()):
            self.streamOut = sys.stdout.write
            self.streamFlush = sys.stdout.flush

        if stream == 2 and os.isatty(sys.stderr.fileno()):
            self.streamOut = sys.stderr.write
            self.streamFlush = sys.stderr.flush

        elif hasattr(stream, 'write'):
            self.streamOut = stream.write
            self.streamFlush = stream.flush

        old_settings = None
        breakflag = None
        fd = sys.stdin.fileno() #标准输入的文件描述符
        def getChar(self):
            nonlocal old_settings
            nonlocal breakflag
            #保存标准输入的属性
            old_settings = termios.tcgetattr(fd)

           #标准输入设为原始模式
            tty.setraw(sys.stdin.fileno())
            #读取一个字符
            ch = sys.stdin.read(1) #用于用户中断，按任意键均可中断
            breakflag = True if ch else False
        #创建线程
        getChar = threading.Thread(target = getChar)

        #设置为守护线程
        getChar.daemon = True
        #启动守护线程
        getChar.start()
        rows = len(self.charVideo[0])//os.get_terminal_size()[0]
        for frame in self.charVideo:
            if breakflag is True:
                break
            self.streamOut(frame)
            self.streamFlush()
            time.sleep(self.timeInterval)
            #一共有row行,光标上移row-1行，回到开始的地方
            self.streamOut('\033[{}A\r'.format(rows-1)) #光标向上移动，去掉一行
        #恢复标准输入的属性
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        self.streamOut('\033[{}B\033[K'.format(rows - 1)) #光标向下移动，去掉最后一行
        info = 'User Interrupt! \n' if breakflag else 'Finished \n'
        self.streamOut(info)
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help = 'Video File or Charvideo File')
    parser.add_argument('-e', '--export', nargs = '?', const = 'charvideo.txt',
                        help='Export charvideo file')
    #get info
    args = parser.parse_args()
    v2char = V2Char(args.file)
    if args.export:
        v2char.export(args.export)
    v2char.play()