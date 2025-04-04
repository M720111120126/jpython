import sys, urllib.request, json, random, platform, subprocess, struct, win32api, win32con, win32gui_struct, win32gui
from decimal import Decimal, getcontext
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
class sys_tray_icon(object):
    """SysTrayIcon类用于显示任务栏图标"""
    QUIT = 'QUIT'
    SPECIAL_ACTIONS = [QUIT]
    FIRST_ID = 5320
    def __init__(self, icon, hover_text, menu_options, on_quit, tk_window=None, default_menu_index=None,
                 window_class_name=None):
        """
        icon         需要显示的图标文件路径
        hover_text   鼠标停留在图标上方时显示的文字
        menu_options 右键菜单，格式: (('a', None, callback), ('b', None, (('b1', None, callback),)))
        on_quit      传递退出函数，在执行退出时一并运行
        tk_window    传递Tk窗口，s.root，用于单击图标显示窗口
        default_menu_index 不显示的右键菜单序号
        window_class_name  窗口类名
        """
        self.icon = icon
        self.hover_text = hover_text
        self.on_quit = on_quit
        self.root = tk_window
        #  右键菜单添加退出
        menu_options = menu_options + (('退出', None, self.QUIT),)
        # 初始化托盘程序每个选项的ID，后面的依次+1
        self._next_action_id = self.FIRST_ID
        self.menu_actions_by_id = set()
        self.menu_options = self._add_ids_to_menu_options(list(menu_options))
        self.menu_actions_by_id = dict(self.menu_actions_by_id)
        del self._next_action_id
        self.default_menu_index = (default_menu_index or 0)
        self.window_class_name = window_class_name or "SysTrayIconPy"
        message_map = {win32gui.RegisterWindowMessage("TaskbarCreated"): self.restart,
                       win32con.WM_DESTROY: self.destroy,
                       win32con.WM_COMMAND: self.command,
                       win32con.WM_USER + 20: self.notify, }
        # 注册窗口类。
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32gui.GetModuleHandle(None)
        wc.lpszClassName = self.window_class_name
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map  # 也可以指定wndproc.
        self.classAtom = win32gui.RegisterClass(wc)
    def activation(self):
        """激活任务栏图标，不用每次都重新创建新的托盘图标"""
        hinst = win32gui.GetModuleHandle(None)  # 创建窗口。
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(self.classAtom,
                                          self.window_class_name,
                                          style,
                                          0, 0,
                                          win32con.CW_USEDEFAULT,
                                          win32con.CW_USEDEFAULT,
                                          0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)
        self.notify_id = None
        self.refresh(title='软件已后台！', msg='软件已后台', time=500)
        win32gui.PumpMessages()
    def refresh(self, title='', msg='', time=500):
        """刷新托盘图标
           title 标题
           msg   内容，为空的话就不显示提示
           time  提示显示时间"""
        hinst = win32gui.GetModuleHandle(None)
        hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        if self.notify_id:
            message = win32gui.NIM_MODIFY
        else:
            message = win32gui.NIM_ADD

        self.notify_id = (self.hwnd, 0,  # 句柄、托盘图标ID
                          win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP | win32gui.NIF_INFO,
                          # 托盘图标可以使用的功能的标识
                          win32con.WM_USER + 20, hicon, self.hover_text,  # 回调消息ID、托盘图标句柄、图标字符串
                          msg, time, title,  # 提示内容、提示显示时间、提示标题
                          win32gui.NIIF_INFO  # 提示用到的图标
                          )
        win32gui.Shell_NotifyIcon(message, self.notify_id)
    def show_menu(self):
        """显示右键菜单"""
        menu = win32gui.CreatePopupMenu()
        self.create_menu(menu, self.menu_options)

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(menu,
                                win32con.TPM_LEFTALIGN,
                                pos[0],
                                pos[1],
                                0,
                                self.hwnd,
                                None)
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
    # 整理菜单的选项，添加ID.递归添加，将二级菜单页添加进去
    def _add_ids_to_menu_options(self, menu_options):
        result = []
        for menu_option in menu_options:
            option_text, option_icon, option_action = menu_option
            if callable(option_action) or option_action in self.SPECIAL_ACTIONS:
                self.menu_actions_by_id.add((self._next_action_id, option_action))
                result.append(menu_option + (self._next_action_id,))
            else:
                result.append((option_text,
                               option_icon,
                               self._add_ids_to_menu_options(option_action),
                               self._next_action_id))
            self._next_action_id += 1
        return result
    def restart(self, hwnd, msg, wparam, lparam):
        self.refresh()
    def destroy(self, hwnd=None, msg=None, wparam=None, lparam=None, _exit=1):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)  # 终止应用程序。
        if _exit and self.on_quit:
            self.on_quit()  # 需要传递自身过去时用 s.on_quit(s)
        else:
            self.root.deiconify()  # 显示tk窗口
    def notify(self, hwnd, msg, wparam, lparam):
        """鼠标事件"""
        if lparam == win32con.WM_LBUTTONDBLCLK:  # 双击左键
            pass
        elif lparam == win32con.WM_RBUTTONUP:  # 右键弹起
            self.show_menu()
        elif lparam == win32con.WM_LBUTTONUP:  # 左键弹起
            self.destroy(_exit=0)
        return True
    def create_menu(self, menu, menu_options):
        for option_text, option_icon, option_action, option_id in menu_options[::-1]:
            if option_icon:
                option_icon = self.prep_menu_icon(option_icon)

            if option_id in self.menu_actions_by_id:
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                wID=option_id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
            else:
                submenu = win32gui.CreatePopupMenu()
                self.create_menu(submenu, option_action)
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                hSubMenu=submenu)
                win32gui.InsertMenuItem(menu, 0, 1, item)
    def prep_menu_icon(self, icon):
        # 加载图标。
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYSMICON)
        hicon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON, ico_x, ico_y, win32con.LR_LOADFROMFILE)
        hdcBitmap = win32gui.CreateCompatibleDC(0)
        hdcScreen = win32gui.GetDC(0)
        hbm = win32gui.CreateCompatibleBitmap(hdcScreen, ico_x, ico_y)
        hbmOld = win32gui.SelectObject(hdcBitmap, hbm)
        brush = win32gui.GetSysColorBrush(win32con.COLOR_MENU)
        win32gui.FillRect(hdcBitmap, (0, 0, 16, 16), brush)
        win32gui.DrawIconEx(hdcBitmap, 0, 0, hicon, ico_x, ico_y, 0, 0, win32con.DI_NORMAL)
        win32gui.SelectObject(hdcBitmap, hbmOld)
        win32gui.DeleteDC(hdcBitmap)
        return hbm
    def command(self, hwnd, msg, wparam, lparam):
        _id = win32gui.LOWORD(wparam)
        self.execute_menu_option(_id)

    def execute_menu_option(self, _id):
        menu_action = self.menu_actions_by_id[_id]
        if menu_action == self.QUIT:
            win32gui.DestroyWindow(self.hwnd)
        else:
            menu_action(self)
help_old = help
open_old = open
eval_old = eval
exec_old = exec
_terminal_prompt = 0
def terminal_prompt() -> None:
    global _terminal_prompt
    if _terminal_prompt == 0:
        _terminal_prompt = 1
    else:
        _terminal_prompt = 0
    return None
def help() -> None:
    print("""Welcome to the Jython (Python Upgraded Version) Helper!
If this is your first time using Jython, you should definitely use help().

Jpthon1.0.0
Jython特有函数
help------------------------帮助
terminal_prompt-------------终端提示启动/关闭
Link_API--------------------调用API
Heographical_Position-------获取电脑的地理位置
Network_Access--------------网络接入
Start file or software------启动文件或软件
High_precision_calculation--高精度运算
run_command_hidden----------没有窗口运行command
Obtain_file_permissions-----获取文件权限
infinity--------------------无限大
tk_pro----------------------高级tk窗口""")
    help_old()
    return None
def open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, w='', modepro=('', '')):
    if _terminal_prompt == 1:
        print(f'file:{file},mode:{mode},encoding:{encoding}')
    if mode == 'r_pro':
        f = open_old(file, 'r', buffering, encoding, errors, newline, closefd, opener)
        content = f.read()
        f.close()
        return content
    elif mode == 'w_pro':
        f = open_old(file, 'w', buffering, encoding, errors, newline, closefd, opener)
        f.write(w)
        f.close()
        return None
    elif mode == 'pro':
        (mode2, types) = modepro
        if types == 'r':
            f = open_old(file, mode2, buffering, encoding, errors, newline, closefd, opener)
            content = f.read()
            f.close()
            return content
        elif types == 'w':
            f = open_old(file, mode2, buffering, encoding, errors, newline, closefd, opener)
            f.write(w)
            f.close()
            return None
        else:
            sys.exit('''Jython->Open->ModePro is error:
The modepro of the open function in Jython is incorrect. If the open mode uses pro, then modepro needs to input (mode, type) such as: ('rb ',' r ')''')
    open_old(file, mode, buffering, encoding, errors, newline, closefd, opener)
def Link_API(URL:str, GetOrPost:str='Get', Post:bytes=b'', encoding:str='utf-8') -> dict:
    BANBENG = platform.system() + " NT " + str(float(platform.release()))  # 获取系统版本号
    headers = {
        "User-Agent": "Mozilla/5.0 (" + BANBENG + "; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.188",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Charset": "utf-8", "Accept-Language": "zh-CN", "Connection": "close"}  # 伪装成浏览器
    try:
        if GetOrPost == 'Get':
            req = urllib.request.Request(URL)
            if _terminal_prompt == 1:
                print(f'Get {URL}')
            return json.loads(urllib.request.urlopen(req).read().decode(encoding))
        elif GetOrPost == 'Post':
            req = urllib.request.Request(URL)
            if _terminal_prompt == 1:
                print(f'Post {URL}')
            return json.loads(urllib.request.urlopen(req).read().decode(encoding))
        else:
            sys.exit('''Jython->Link_API->GetOrPost is error:
The GetOrPost of the Link-API function in Jython is incorrect. If you want to access the API through POST, GetOrPost needs to input Post, which needs to input the content of Post (in bytes format).''')
    except:
        if GetOrPost == 'Get':
            req = urllib.request.Request(URL,headers=headers)
            if _terminal_prompt == 1:
                print(f'Get {URL},disguised as a browser')
            return json.loads(urllib.request.urlopen(req).read().decode(encoding))
        elif GetOrPost == 'Post':
            req = urllib.request.Request(URL, headers=headers)
            if _terminal_prompt == 1:
                print(f'Post {URL},disguised as a browser')
            return json.loads(urllib.request.urlopen(req).read().decode(encoding))
        else:
            sys.exit('''Jython->Link_API->GetOrPost is error:
The GetOrPost of the Link-API function in Jython is incorrect. If you want to access the API through POST, GetOrPost needs to input Post, which needs to input the content of Post (in bytes format).''')
def bing(f) ->bool:
    try:
        response = urllib.request.urlopen('https://api.oioweb.cn/api/bing')
        with open(f, 'wb') as f:
            f.write(urllib.request.urlopen(
                json.loads(response.read().decode('utf-8'))["result"][int(random.uniform(1, 7))]["url"]).read())
        return True
    except:
        return False
def Heographical_Position() ->dict:
    try:
        response = urllib.request.urlopen('https://api.uomg.com/api/visitor.info?skey=774740085')
        response = urllib.request.urlopen(
            'https://api.oioweb.cn/api/ip/ipaddress?ip=' + json.loads(response.read().decode('utf-8'))["ip"])
        return json.loads(response.read().decode('utf-8'))["result"]["addr"][0]
    except:
        return {}
def Network_access(URL:str, headers:dict=None, get_or_post:str= 'Get', Post:bytes= b'', encoding:str= 'utf-8') ->dict:
    if headers is None:
        BANBENG = platform.system() + " NT " + str(float(platform.release()))  # 获取系统版本号
        arch = platform.architecture()  # 获取系统位数
        arch2 = struct.calcsize("P")  # 获取Python解释器位数
        if (arch == '64bit') and (arch2 == 4):
            B2 = 'WOW64'
        elif (not (arch == '64bit')) and (arch2 == 4):
            B2 = 'Win32'
        elif (arch == '64bit') and (not(arch2 == 4)):
            B2 = 'Win64; x64'
        else:
            B2 = ''
        headers = {
            "User-Agent": "Mozilla/5.0 (" + BANBENG + "; " + B2 + ") AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.188",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Charset": "utf-8", "Accept-Language": "zh-CN", "Connection": "close"
        }  # 伪装成浏览器
    try:
        if get_or_post == 'Get':
            req = urllib.request.Request(URL)
            if _terminal_prompt == 1:
                print(f'Get {URL}')
            return json.loads(urllib.request.urlopen(req).read().decode(encoding))
        elif get_or_post == 'Post':
            req = urllib.request.Request(URL)
            if _terminal_prompt == 1:
                print(f'Post {URL}')
            return json.loads(urllib.request.urlopen(req).read().decode(encoding))
        else:
            sys.exit('''Jython->Network_Access->GetOrPost is error:
    The GetOrPost of the Network_Access function in Jython is incorrect. If you want to access the API through POST, GetOrPost needs to input Post, which needs to input the content of Post (in bytes format).''')
    except:
        if get_or_post == 'Get':
            req = urllib.request.Request(URL, headers=headers)
            if _terminal_prompt == 1:
                print(f'Get {URL},disguised as a browser')
            return json.loads(urllib.request.urlopen(req).read().decode(encoding))
        elif get_or_post == 'Post':
            req = urllib.request.Request(URL, headers=headers)
            if _terminal_prompt == 1:
                print(f'Post {URL},disguised as a browser')
            return json.loads(urllib.request.urlopen(req).read().decode(encoding))
        else:
            sys.exit('''Jython->Network_Access->GetOrPost is error:
    The GetOrPost of the Network_Access function in Jython is incorrect. If you want to access the API through POST, GetOrPost needs to input Post, which needs to input the content of Post (in bytes format).''')
def eval() ->None:
    print('程序正在调用危险函数，已进行拦截')
    return None
def exec() ->None:
    print('程序正在调用危险函数，已进行拦截')
    return None
def Start_file_or_software(f) ->None:
    run_command_hidden(f)
    return None
def High_precision_calculation(data:list, formula:str) ->float:
    ABC = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
           'V', 'W', 'X', 'Y', 'Z']
    for i in list(range(len(data))):
        eval_old(ABC[i] + '=' + str(Decimal(data[i])))
    getcontext().prec = 3
    return eval_old(formula)
def run_command_hidden(command) ->None:
    # 定义一个STARTUPINFO对象，该对象有着与C语言中STARTUPINFO结构体相同的属性
    startupinfo = subprocess.STARTUPINFO()
    # 这个选项确保了子进程的窗口是隐藏的
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    # 使用Popen来启动子进程，传递要执行的命令和参数列表
    # 注意，我们传递了上面创建的startupinfo对象
    process = subprocess.Popen(command, startupinfo=startupinfo)
    # 等待子进程完成
    process.wait()
    return None
def Obtain_file_permissions(f) ->None:
    # 获取TrustedInstaller权限的命令
    command = 'takeown /f "%1" && icacls "%1" /grant administrators:F'
    # 替换 %1 为你想要获取权限的文件或文件夹的路径
    file_path = 'C:\\example.txt'
    command = command % f
    # 执行命令，不显示cmd窗口
    run_command_hidden(command)
    return None
def infinity() ->float:
    return float('infinity')
class _tk_pro:  # 调用SysTrayIcon的Demo窗口
    def __init__(self, icon, name):
        self.SysTrayIcon = None  # 判断是否打开系统托盘图标
        self.icon = icon
        self.name = name
    def main(self):
        self.s = tk.Tk()
        self.s.bind("<Unmap>", lambda event: self.Hidden_window(self.icon, self.name) if self.s.state() == 'iconic' else False)
        self.s.protocol('WM_DELETE_WINDOW', self.guanbi)
        self.s.mainloop()
    def guanbi(self):
        res = tk.messagebox.askokcancel('提示', '是否退出？')
        if res:
            sys.exit()
    def Hidden_window(self, icon='', hover_text="SysTrayIcon.py Demo"):
        self.s.protocol('WM_DELETE_WINDOW', self.exit)
        # 托盘图标右键菜单, 格式: ('name', None, callback),下面也是二级菜单的例子
        # 15行有自动添加‘退出’，不需要的可删除
        menu_options = ()
        self.s.withdraw()  # 隐藏tk窗口
        if not self.SysTrayIcon: self.SysTrayIcon = sys_tray_icon(
            icon,  # 图标
            hover_text,  # 光标停留显示文字
            menu_options,  # 右键菜单
            on_quit=self.exit,  # 退出调用
            tk_window=self.s,  # Tk窗口
        )
        self.SysTrayIcon.activation()
        self.s.protocol('WM_DELETE_WINDOW', self.guanbi)
    def exit(self, _sysTrayIcon=None):
        self.guanbi()
    def init(self):
        return self.s
def tk_pro(icon='', name='python'):
    win = _tk_pro(icon, name)
    win.main()
    return win.init()