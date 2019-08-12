import tkinter as tk
from tkinter import ttk
from tkinter import messagebox,filedialog
import telnetlib
import threading,time,queue,os,re
from configparser import ConfigParser
import traceback
import logging,logging.config

logging.config.fileConfig("logger.conf")
logger_out = logging.getLogger("example01")
logger_err = logging.getLogger("example02")

# ---------logger_out--------
def debug(message):
   logger_out.debug(message)

def warning(message):
    logger_out.warning(message)

def info(message):
    logger_out.info(message)

def error(message):
    logger_out.error(message)

# ---------logger_err--------
def debug_err(message):
   logger_err.debug(message)

def error_err(message):
    logger_err.error(message)


class Gvar:
    que_for_post_check = queue.Queue()
    post_threadnum = 1
    re_upgrade_threadnum = 1
    post_check_flag_done = True

def login_slave(tn):
    tn.read_until(b'NAME]:', timeout=5)
    tn.write(b'admin\r\n')
    res = tn.read_until(b'SSWORD]:|>>', timeout=5)
    if b'SSWORD' in res:
        tn.write(b'admin\r\n')
        res = tn.read_until(b'>>', timeout=5)
    if b'Welcome' not in res:
        return False
    return True

def login(tn):
    tn.read_until(b'ogin:', timeout=5)
    tn.write(b'admin\r\n')
    res = tn.read_until(b'ssword:|#', timeout=5)
    if b'ssword' in res:
        tn.write(b'admin\r\n')
        res = tn.read_until(b'#', timeout=5)
    if b'rivileged' not in res:
        return False
    return True

def exe_cli(tn, com, exp=b'#', tmo=6):
    tn.write(com)
    res = b''
    while tmo:
        try:
            result = tn.read_until((exp or b'quit)'), timeout=2)
        except Exception as e:
            print(e)
            return False
        res = res + result + b'\r\n'
        if exp in result:
            return res.decode(errors='ignore')
        elif b'quit' in result:
            tn.write(b'\r\n')
        else:
            tmo -=1
    return False

def ipcheck(ip):
    ip=ip.strip()
    iplist=ip.split('.')
    if len(iplist)==4:
        if int(iplist[0])>0 and int(iplist[0])<224:
            if int(iplist[1])>=0 and int(iplist[1])<256:
                if int(iplist[2])>=0 and int(iplist[2])<256:
                    if int(iplist[3])>0 and int(iplist[3])<255:
                        return
                    else:
                        raise ('ip address err')
                    pass
                else:
                    raise ('ip address err')
                pass
            else:
                raise ('ip address err')
            pass
        else:
            raise ('ip address err')
        pass
    else:
        raise ('ip address err')
    pass

def get_dev(tn):
    tn.write(b'show system\r\n')
    res = tn.read_until(b'#',timeout=2)
    if b'#' in res:
        res = res.decode(errors='ignore')
        dev = re.findall(r'iAN\s+(\w+)\s+MSAP',res)
        return dev[0]
    return False

def get_shelves(tn):
    tn.write(b'shelfstack show\r\n')
    result = tn.read_until(b'#', timeout=6)
    result = result.decode()
    mx = re.findall(r'Shelf\s+Max:\s*(\d)', result)
    return int(mx[0])

def pingTest(ip):
    res = os.system("ping -n 5 -w 1 %s" % ip)
    if res:
        return 0
    else:
        return 1

def quit2():
    if Gvar.post_check_flag_done:
        root.destroy()
    else:
        myapp.breakflag = True
        messagebox.showwarning('Warning', 'Cancel task first before close window.')

class Config(object):
    def __init__(self,config_file_path):
        if not os.path.exists(config_file_path):
            raise FileNotFoundError("file %s not exist." % config_file_path)
        self.config_file_path = config_file_path
        self.config = ConfigParser()
        self.config.read(self.config_file_path, encoding="utf-8")


    def get_all_items(self,section):
        return dict(self.config.items(section))

    def get_val(self,section,key,type=None):
        if type == "int":
            return self.config.getint(section,key)
        elif type == "float":
            return self.config.getfloat(section, key)
        else:
            return self.config[section][key]
            # return self.config.get(section, key)


class Post_Check(threading.Thread):
    def __init__(self,q, d):
        threading.Thread.__init__(self)
        self.que = q
        self.dict = d.copy()


    def ebm_check(self, tn, ab):
        """check EBAN的版本"""
        # 当版本check失败的时候，flag显示为True
        flag = False
        tn.write(b'telnet 192.168.180.2 343\r\n')
        info("telnet EBAM success")
        if login_slave(tn):
            tn.write(b'show version\r\n')
            res = tn.read_until(b'>>', timeout=8)
            if b'>>' in res:
                res = res.decode(errors='ignore')
                for line in res.split('\r\n'):
                    info(line.strip())
                for line in res.split('\r\n'):
                    try:
                        if 'Release' in line:
                            if self.dict["bbbb Version"]['release version'] not in line:
                                myapp.text_check.insert('end', ab + ' EBM version mismatch\n')
                                myapp.text_check.yview_moveto(1)
                                warning(ab + ' EBM version mismatch')
                                flag = True
                        elif 'DTB' in line:
                            if self.dict["bbbb Version"]['dtb version'] not in line:
                                myapp.text_check.insert('end', ab + ' EBM DTB version mismatch\n')
                                myapp.text_check.yview_moveto(1)
                                warning(ab + ' EBM DTB version mismatch')
                                flag = True
                        elif 'Uboot' in line:
                            if self.dict["bbbb Version"]['uboot version'] not in line:
                                myapp.text_check.insert('end', ab + ' EBM Uboot version mismatch\n')
                                myapp.text_check.yview_moveto(1)
                                warning(ab + ' EBM Uboot version mismatch')
                                flag = True
                        elif 'Kernel' in line:
                            if self.dict["bbbb Version"]['kernel version'] not in line:
                                myapp.text_check.insert('end', ab + ' EBM Kernel version mismatch\n')
                                myapp.text_check.yview_moveto(1)
                                warning(ab + ' EBM Kernel version mismatch')
                                flag = True
                        elif 'Root' in line:
                            if self.dict["bbbb Version"]['rootfs version'] not in line:
                                myapp.text_check.insert('end', ab + ' EBM root version mismatch\n')
                                myapp.text_check.yview_moveto(1)
                                warning(ab + ' EBM root version mismatch')
                                flag = True
                        else:
                            pass
                    except Exception as e:
                        error_err(traceback.format_exc())
                tn.write(b'exit\r\n')
                tn.read_until(b'[N]:', timeout=5)
                tn.write(b'y\r\n')
                res = tn.read_until(b'#', timeout=5)
                info('logout EBM...')
            elif b'#' in res:
                myapp.text_check.insert('end',ab + ' EBM unexpect exit!\n')
                myapp.text_check.yview_moveto(1)
                error(ab + ' EBM unexpect exit!')
                flag = True
            else:
                tn.write(b'\r\n')
                tn.write(b'exit\r\n')
                res = tn.read_until(b'#', timeout=5)
                myapp.text_check.insert('end',ab + ' EBM no response!\n')
                myapp.text_check.yview_moveto(1)
                warning(ab + ' EBM no response!')
                flag = True
        else:
            myapp.text_check.insert('end',ab + ' EBM login fail\n')
            myapp.text_check.yview_moveto(1)
            warning(ab + ' EBM login fail')
            flag = True
        return flag

    def run(self):

        while True:
            if myapp.breakflag:
                myapp.text_check.insert('end', 'Cancelled all tasks...\n')
                myapp.text_check.yview_moveto(1)
                info('Cancelled all tasks.')
                Gvar.post_check_flag_done = True
                break
            if self.que.empty():
                Gvar.post_check_flag_done = True
                break

            _ip = self.que.get(True, 2)
            if not pingTest(_ip):
                myapp.text_check.insert('end',"%s ping fail...\n" % _ip)
                myapp.text_check.yview_moveto(1)
                error("%s ping fail..." % _ip)
                continue

            try:
                tn = telnetlib.Telnet(_ip,23,timeout=5)
            except Exception as e:
                myapp.text_check.insert('end', "%s telnet fail...\n" % _ip)
                myapp.text_check.yview_moveto(1)
                error("%s telnet fail..." % _ip)
                error_err(traceback.format_exc())
                continue
            if not login(tn):
                tn.close()
                myapp.text_check.insert('end', "%s login fail...\n" % _ip)
                myapp.text_check.yview_moveto(1)
                warning("%s login fail..." % _ip)
                continue
            if not get_dev(tn):
                myapp.text_check.insert('end', 'find %s device type fail...\n' % _ip)
                myapp.text_check.yview_moveto(1)
                warning('find %s device type fail...' % _ip)
                continue

            if get_dev(tn) == "aaaa":
                myapp.text_check.insert('end', '%s telnet success and checking version...\n' % _ip)
                myapp.text_check.yview_moveto(1)
                myapp.text_check.update()
                info('%s telnet success and checking version...' % _ip)

                # 登录进去获取shelf的数量
                _shelves = get_shelves(tn)

                # shelf没有异常的时候显示为False
                shelf_health = False
                for _port in range(_shelves):
                    myapp.text_check.insert('end', "%s shelf %s check start...\n" % (_ip,str(_port+1)))
                    myapp.text_check.yview_moveto(1)
                    info("%s shelf %s check start..." % (_ip,str(_port+1)))
                    if _port != 0:
                        try:
                            tn = telnetlib.Telnet(_ip, _port + 23, timeout=6)
                        except Exception as e:
                            shelf_health = True
                            error_err(traceback.format_exc())
                            continue
                        else:
                            if not login(tn):
                                tn.close()
                                shelf_health = True
                                continue
                    try:
                        res = exe_cli(tn, b'display gn\r\n', exp=b'#', tmo=10)
                        if not res:
                            shelf_health = True
                            continue
                        # 对比成功的时候flag为FALSE
                        flag = False
                        res_new = res.replace('display gn','show slot')
                        for line in res_new.split('\r\n'):
                            info(line.strip())
                        for line in res.split('\r\n'):
                            if 'CSM' in line:
                                if self.dict["aaaa Version"]['csm1a'] not in line:
                                    mat = re.findall('(\d-\w)', line)
                                    myapp.text_check.insert('end', '%s %s CSM1A version mismatch\n' % (_ip,mat[0]))
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s %s CSM1A version mismatch' % (_ip,mat[0]))
                                    flag = True
                            elif 'ASL' in line:
                                if self.dict["aaaa Version"]['asl1a'] not in line:
                                    mat = re.findall('(\d-\d+)', line)
                                    myapp.text_check.insert('end', '%s %s ASL1A version mismatch\n' % (_ip,mat[0]))
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s %s ASL1A version mismatch' % (_ip,mat[0]))
                                    flag = True
                            elif 'VPM' in line:
                                if self.dict["aaaa Version"]['vpm1a'] not in line:
                                    mat = re.findall('(\d-\w+)', line)
                                    myapp.text_check.insert('end', '%s %s VPM1A version mismatch\n' % (_ip,mat[0]))
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s %s VPM1A version mismatch' % (_ip, mat[0]))
                                    flag = True
                            elif 'FXS2F' in line:
                                if self.dict["aaaa Version"]['fxs2f'] not in line:
                                    mat = re.findall('(\d-\d+)', line)
                                    myapp.text_check.insert('end', '%s %s FXS2F version mismatch\n' % (_ip, mat[0]))
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s %s FXS2F version mismatch' % (_ip, mat[0]))
                                    flag = True
                            elif 'FXS1A' in line:
                                if self.dict["aaaa Version"]['fxs1a'] not in line:
                                    mat = re.findall('(\d-\d+)', line)
                                    myapp.text_check.insert('end', '%s %s FXS1A version mismatch\n' % (_ip, mat[0]))
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s %s FXS1A version mismatch' % (_ip, mat[0]))
                                    flag = True
                            else:
                                pass
                        _act = re.findall(r'(1-\w)\s+CSM1A', res, re.M)
                        if len(_act) != 2:
                            myapp.text_check.insert('end', '%s No standby CSM\n' % _ip)
                            myapp.text_check.yview_moveto(1)
                            warning('%s No standby CSM' % _ip)
                            flag = True
                        _act = re.findall(r'(1-\w)\s+CSM1A\(A\)', res, re.M)
                        if '1-A' in _act:
                            _stdby = b'telnet 192.168.200.2\r\n'
                            act_slot = 'A'
                        else:
                            _stdby = b'telnet 192.168.200.1\r\n'
                            act_slot = 'B'
                        if 'FXS2F' in res:
                            res = exe_cli(tn, b'show cpld\r\n')
                            for line in res.split("\r\n"):
                                info(line.strip())
                            mat = re.findall('(\d:\d)\s+(\d+)', res, re.M)
                            if mat:
                                for item in mat:
                                    if (item[0] != self.dict["aaaa Version"]['fxs_cpld']) or (item[1] != self.dict["aaaa Version"]['fxs_bios']):
                                        myapp.text_check.insert('end','%s shelf %s FXS cpld/bios mismatch\n' % (_ip,str(_port+1)))
                                        myapp.text_check.yview_moveto(1)
                                        warning('%s shelf %s FXS cpld/bios mismatch\n' % (_ip,str(_port+1)))
                                        flag = True
                            else:
                                flag = True
                        if flag:
                            shelf_health = True
                    except Exception as e:
                        tn.close()
                        # error_err(traceback.format_exc())
                        myapp.text_check.insert('end', 'telnet unexpect exit\n')
                        myapp.text_check.yview_moveto(1)
                        error('telnet unexpect exit')
                        shelf_health = True
                        continue
                    tn.close()
                if not shelf_health:
                    myapp.text_check.insert('end', 'check %s success\n' % _ip)
                    myapp.text_check.yview_moveto(1)
                    myapp.text_check.update()
                    info('check %s success.' % _ip)
                Gvar.post_check_flag_done = True
                if myapp.breakflag:
                    myapp.text_check.insert('end', 'Cancelled all tasks\n')
                    myapp.text_check.yview_moveto(1)
                    info('Cancelled all tasks.')
                    break
                else:
                    myapp.text_check.insert('end', 'Finished %s check\n' % _ip)
                    myapp.text_check.yview_moveto(1)
                    info('Finished %s check.' % _ip)
                myapp.text_check.yview_moveto(1)
                myapp.text_check.update()

            elif get_dev(tn) == "bbbb":
                flag = False
                _slave = False

                myapp.text_check.insert('end',  '%s telnet success and checking version...\n' % _ip)
                myapp.text_check.yview_moveto(1)
                myapp.text_check.update()
                info('%s telnet success and checking version...' % _ip)
                try:
                    res = exe_cli(tn, b'display gn\r\n', exp=b'#', tmo=10)
                    if not res:
                        myapp.text_check.insert('end', '%s show slot fail\n' % _ip)
                        myapp.text_check.yview_moveto(1)
                        warning('%s show slot fail' % _ip)
                        tn.close()
                        continue
                    res_new = res.replace('display gn','show slot')
                    for line in res_new.split('\r\n'):
                        info(line.strip())
                    for line in res.split('\r\n'):
                        if 'ASL' in line:
                            if self.dict["bbbb Version"]['asl1a'] not in line:
                                mat = re.findall('(\d-\d+)', line)
                                myapp.text_check.insert('end', '%s %s ASL1A version mismatch\n' % (_ip,mat[0]))
                                myapp.text_check.yview_moveto(1)
                                warning('%s %s ASL1A version mismatch' % (_ip,mat[0]))
                                flag = True
                        elif 'VPM' in line:
                            if self.dict["bbbb Version"]['vpm1a'] not in line:
                                mat = re.findall('(\d-\w+)', line)
                                myapp.text_check.insert('end', '%s %s VPM1A version mismatch\n' % (_ip, mat[0]))
                                myapp.text_check.yview_moveto(1)
                                warning('%s %s VPM1A version mismatch' % (_ip, mat[0]))
                                flag = True
                        elif 'FXS2F' in line:
                            if self.dict["bbbb Version"]['fxs2f'] not in line:
                                mat = re.findall('(\d-\d+)', line)
                                myapp.text_check.insert('end', '%s %s FXS2F version mismatch\n' % (_ip, mat[0]))
                                myapp.text_check.yview_moveto(1)
                                warning('%s %s FXS2F version mismatch' % (_ip, mat[0]))
                                flag = True
                        elif 'FXS1A' in line:
                            if self.dict["bbbb Version"]['fxs1a'] not in line:
                                mat = re.findall('(\d-\d+)', line)
                                myapp.text_check.insert('end', '%s %s FXS1A version mismatch\n' % (_ip, mat[0]))
                                myapp.text_check.yview_moveto(1)
                                warning('%s %s FXS1A version mismatch' % (_ip, mat[0]))
                                flag = True
                        else:
                            pass
                    _act = re.findall(r'(1-\w)\s+CSM1F', res, re.M)
                    if len(_act) != 2:
                        myapp.text_check.insert('end', '%s No standby CSM\n' % _ip)
                        myapp.text_check.yview_moveto(1)
                        warning('%s No standby CSM' % _ip)
                        flag = True
                    _act = re.findall(r'(1-\w)\s+CSM1F\(A\)', res, re.M)
                    if '1-A' in _act:
                        _stdby = b'telnet 172.31.6.36\r\n'
                        act_slot = 'A'
                    else:
                        _stdby = b'telnet 172.31.6.34\r\n'
                        act_slot = 'B'
                    if re.search(r'EBM1F.*\d\.\d\.\d\.\d+', res, re.M):
                        _slave = True
                        if self.ebm_check(tn, 'Act'):
                            myapp.text_check.insert('end', '%s slot %s EBM1F fail\n' % (_ip,act_slot))
                            myapp.text_check.yview_moveto(1)
                            warning('%s slot %s EBM1F fail' % (_ip,act_slot))
                            flag = True
                    tn.write(b'display gnver\r\n')
                    res = tn.read_until(b'#', timeout=8)
                    res = res.decode(errors='ignore')
                    res_new = res.replace('display gnver','show version')
                    for line in res_new.split('\r\n'):
                        info(line.strip())
                    for line in res.split('\r\n'):
                        if 'cpld' in line:
                            if self.dict["bbbb Version"]['cpld_version'] not in line:
                                myapp.text_check.insert('end', '%s ACT CSM cpld version mismatch\n' % _ip)
                                myapp.text_check.yview_moveto(1)
                                warning('%s ACT CSM cpld version mismatch' % _ip)
                                flag = True
                        elif 'app' in line:
                            if self.dict["bbbb Version"]['app_version'] not in line:
                                myapp.text_check.insert('end', '%s ACT app version mismatch\n' % _ip)
                                myapp.text_check.yview_moveto(1)
                                warning('%s ACT app version mismatch' % _ip)
                                flag = True
                        elif 'dtb' in line:
                            if self.dict["bbbb Version"]['dtb_version'] not in line:
                                myapp.text_check.insert('end', '%s ACT dtb version mismatch\n' % _ip)
                                myapp.text_check.yview_moveto(1)
                                warning('%s ACT dtb version mismatch' % _ip)
                                flag = True
                        elif 'uboot' in line:
                            if self.dict["bbbb Version"]['uboot_version'] not in line:
                                myapp.text_check.insert('end', '%s ACT uboot version mismatch\n' % _ip)
                                myapp.text_check.yview_moveto(1)
                                warning('%s ACT uboot version mismatch' % _ip)
                                flag = True
                        elif 'kernel' in line:
                            if self.dict["bbbb Version"]['kernel_version'] not in line:
                                myapp.text_check.insert('end', '%s ACT kernel version mismatch\n' % _ip)
                                myapp.text_check.yview_moveto(1)
                                warning('%s ACT kernel version mismatch' % _ip)
                                flag = True
                        elif 'root' in line:
                            if self.dict["bbbb Version"]['rootfs_version'] not in line:
                                myapp.text_check.insert('end', '%s ACT rootfs version mismatch\n' % _ip)
                                myapp.text_check.yview_moveto(1)
                                warning('%s ACT rootfs version mismatch' % _ip)
                                flag = True
                        else:
                            pass
                    res = exe_cli(tn, b'show cpld\r\n')
                    for line in res.split('\r\n'):
                        info(line.strip())
                    mat = re.findall('(\d:\d)', res, re.M)
                    fcpld = 0
                    for item in mat:
                        if item != self.dict["bbbb Version"]['fxs_cpld']:
                            fcpld += 1
                    if fcpld:
                        myapp.text_check.insert('end', '%s FXS cpld version mismatch\n' % _ip)
                        myapp.text_check.yview_moveto(1)
                        warning('%s FXS cpld version mismatch' % _ip)
                    info('telnet SBY...')
                    tn.write(_stdby)
                    if login(tn):
                        tn.write(b'display gnver\r\n')
                        res = tn.read_until(b'#', timeout=6)
                        res = _stdby + res
                        res = res.decode(errors='ignore')
                        res_new = res.replace('display gnver', 'show version')
                        for line in res_new.split('\r\n'):
                            info(line.strip())
                        for line in res.split('\r\n'):
                            if 'cpld' in line:
                                if self.dict["bbbb Version"]['cpld_version'] not in line:
                                    myapp.text_check.insert('end', '%s Standby CSM cpld mismatch\n' % _ip)
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s Standby CSM cpld mismatch' % _ip)
                                    flag = True
                            elif 'app' in line:
                                if self.dict["bbbb Version"]['app_version'] not in line:
                                    myapp.text_check.insert('end', '%s Standby CSM app version mismatch\n' % _ip)
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s Standby CSM app version mismatch' % _ip)
                                    flag = True
                            elif 'dtb' in line:
                                if self.dict["bbbb Version"]['dtb_version'] not in line:
                                    myapp.text_check.insert('end', '%s Standby CSM dtb mismatch\n' % _ip)
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s Standby CSM dtb mismatch' % _ip)
                                    flag = True
                            elif 'uboot' in line:
                                if self.dict["bbbb Version"]['uboot_version'] not in line:
                                    myapp.text_check.insert('end', '%s Standby CSM uboot mismatch\n' % _ip)
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s Standby CSM uboot mismatch' % _ip)
                                    flag = True
                            elif 'kernel' in line:
                                if self.dict["bbbb Version"]['kernel_version'] not in line:
                                    myapp.text_check.insert('end', '%s Standby CSM kernel mismatch\n' % _ip)
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s Standby CSM kernel mismatch' % _ip)
                                    flag = True
                            elif 'root' in line:
                                if self.dict["bbbb Version"]['rootfs_version'] not in line:
                                    myapp.text_check.insert('end', '%s Standby CSM root mismatch\n' % _ip)
                                    myapp.text_check.yview_moveto(1)
                                    warning('%s Standby CSM root mismatch' % _ip)
                                    flag = True
                            else:
                                pass
                        if _slave:
                            if self.ebm_check(tn, 'Stdby'):
                                myapp.text_check.insert('end', '%s standby EBM1F fail\n' % _ip)
                                myapp.text_check.yview_moveto(1)
                                warning('%s standby EBM1F fail' % _ip)
                                flag = True
                        tn.write(b'exit\r\n')
                    else:
                        myapp.text_check.insert('end', '%s Standby CSM login fail\n' % _ip)
                        myapp.text_check.yview_moveto(1)
                        warning('%s Standby CSM login fail' % _ip)
                        flag = True
                    tn.read_until(b'#', timeout=5)
                    tn.write(b'exit\r\n')

                except Exception as e:
                    tn.close()
                    # error_err(traceback.format_exc())
                    myapp.text_check.insert('end', '%s telnet unexpect exit\n' % _ip)
                    myapp.text_check.yview_moveto(1)
                    error('%s telnet unexpect exit' % _ip)
                tn.close()
                if not flag:
                    myapp.text_check.insert('end', 'check %s success.\n' % _ip)
                    myapp.text_check.yview_moveto(1)
                    myapp.text_check.update()
                    info('check %s success.' % _ip)
                Gvar.post_check_flag_done = True
                if myapp.breakflag:
                    myapp.text_check.insert('end', 'Cancelled all tasks.\n')
                    myapp.text_check.yview_moveto(1)
                    info('Cancelled all tasks.')
                    break
                else:
                    myapp.text_check.insert('end', 'Finished %s check.\n' % _ip)
                    myapp.text_check.yview_moveto(1)
                    myapp.text_check.update()
                    info('Finished %s check.' % _ip)
            else:
                myapp.text_check.insert('end', 'No matching device type...\n')
                myapp.text_check.yview_moveto(1)
                info('No matching device type...')


class App:
    def __init__(self,root):
        self.root = root
        self.breakflag = False
        self.create_content()

    # def get_node_ip(self):
    #     node_ip = self.entry_node_ip.get()
    #     return node_ip

    def create_content(self):

        self.frame1 = ttk.Frame(self.root,padding=(5, 5, 20, 5))
        self.frame1.grid(row=1, column=1,columnspan=4, sticky=(tk.W, tk.N, tk.E))

        # self.node_ip = tk.Label(self.frame1, text="Node IP:")
        # self.node_ip.grid(row=1, column=1, sticky=tk.W)
        self.entry__file_path = tk.Entry(self.frame1,width=40)
        self.entry__file_path.grid(row=1,column=1,padx=5,sticky=(tk.W))

        self.button_import_file = tk.Button(self.frame1,text="Import ips")
        self.button_import_file.grid(row=1,column=2,sticky=(tk.W))
        self.button_import_file["command"] = self.select_file

        # e = tk.StringVar()
        # self.entry_node_ip = ttk.Combobox(self.frame1,textvariable=e)
        # ips = []
        # with open("ips.txt") as fp:
        #     for i in fp:
        #         ips.append(i.strip())
        # self.entry_node_ip['value'] = ips
        # self.entry_node_ip.grid(row=1, column=2, columnspan=2, padx=5, sticky=tk.W)
        self.check_button = tk.Button(self.frame1,text="Check")
        self.check_button.grid(row=1, column=3,padx=10, sticky=(tk.W))
        self.check_button["command"] = self.batchcommand

        self.button_cancel = tk.Button(self.frame1,text="Cancel")
        self.button_cancel.grid(row=1, column=4,sticky=(tk.W))
        self.button_cancel['command'] = self.stop

        self.frame2 = ttk.Frame(self.root, padding=(5, 5, 0, 5))
        self.frame2.grid(row=2, column=1, columnspan=4, sticky=(tk.W, tk.N, tk.E))

        self.frame2 = ttk.Frame(self.root, padding=(5, 5, 0, 5))
        self.frame2.grid(row=2, column=1, columnspan=4, sticky=(tk.W, tk.N, tk.E))

        self.scroll = ttk.Scrollbar(self.frame2, orient="vertical")
        self.scroll.grid(row=2, column=4, sticky=(tk.N, tk.S))

        self.text_check = tk.Text(self.frame2, yscrollcommand=self.scroll.set)
        self.text_check.grid(row=2, column=1, sticky=(tk.W))
        self.scroll.config(command=self.text_check.yview)

        # ttk.Sizegrip().grid(column=99, row=99, sticky=(tk.S, tk.E))
        # self.root.grid_columnconfigure(0, weight=1)
        # self.root.grid_rowconfigure(0, weight=1)

    def select_file(self):
        self.mask = [('number file', '*.txt'), ('All file', '*.*')]
        self.fin = os.getcwd() + '\\ips.txt'
        self.fin = filedialog.askopenfilename(filetypes=self.mask, parent=root)
        self.entry__file_path.delete(0,'end')
        self.entry__file_path.insert('end', self.fin)      #'Entry' object has no attribute 'set'
        #self.numentry['textvariable'] = self.fin
        #self.numentry.update()

    def batchcommand(self):
        self.breakflag = False
        self.versions = {}

        try:
            versionConfig = Config("versions.conf")
            e_version_dict = versionConfig.get_all_items("aaaa Version")
            f_version_dict = versionConfig.get_all_items("bbbb Version")
            e_server_dict = versionConfig.get_all_items("aaaa server")
            self.versions = dict(zip(["aaaa Version","aaaa server","bbbb Version"],[e_version_dict,e_server_dict,f_version_dict]))
        except:
            error_err(traceback.format_exc())
            myapp.text_check.insert('end', 'Parse version file fail...\n')
            myapp.text_check.yview_moveto(1)

        Gvar.que_for_post_check = queue.Queue(200)
        Gvar.post_check_flag_done = False

        self.ipfi = open(self.fin, 'r')
        _que = queue.Queue(200)
        for ipport in self.ipfi:
            ipport = ipport.strip()
            ipp = re.split('\s+', ipport)
            self.ip = ipp[0]
            try:
                ipcheck(self.ip)
            except:
                error_err(traceback.format_exc())
                continue
            else:
                _que.put(self.ip, True, 3)
        self.ipfi.close()

        thread = Post_Check(_que, self.versions)
        thread.start()


    def stop(self):
        if not Gvar.post_check_flag_done:
            self.text_check.insert('end', 'Be patient,  Cancelling...\n')
            self.text_check.yview_moveto(1)
            self.text_check.update()
        self.breakflag = True


if __name__ == '__main__':
    root = tk.Tk(className="Check Version")
    root['padx'] = 5
    root['pady'] = 5
    myapp = App(root)
    root.protocol('WM_DELETE_WINDOW', quit2)
    root.mainloop()