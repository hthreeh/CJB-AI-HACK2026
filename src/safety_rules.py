"""
硬编码的高危操作关键词库，用于在提交给大语言模型前进行前置拦截。
覆盖了自然语言以及常见的破坏性 Shell 命令。
"""

# 1. 关机与重启 (Shutdown and Reboot)
SHUTDOWN_KEYWORDS = [
    "关机", "关闭系统", "停止系统", "断电", "关闭计算机", "关闭电脑", "立刻关机",
    "重启", "重新启动", "重启系统", "重启计算机", "立刻重启",
    "shutdown", "poweroff", "halt", "reboot", "init 0", "init 6"
]

# 2. 破坏性文件操作 (Destructive file operations)
DESTRUCTIVE_FILE_KEYWORDS = [
    "rm -rf /", "rm -rf /*", "rm -rf ~", "rm -rf *", 
    "rm -rf /etc", "rm -rf /boot", "rm -rf /usr", "rm -rf /root", "rm -rf /var",
    "删除根目录", "清空根目录", "删除全部文件", "清空所有文件",
    "删除/etc", "删除 etc", "删除boot", "删除/boot", "删除系统文件",
    "chmod 777 /", "chmod -R 777 /", "chmod 777 -R /"
]

# 3. 破坏性磁盘/文件系统操作 (Destructive disk operations)
DEK_FORMAT_KEYWORDS = [
    "格式化", "格式化磁盘", "格式化硬盘", "mkfs", "擦除磁盘", "清空磁盘", "擦除整个盘",
    "dd if=/dev/zero", "dd if=/dev/urandom", "dd if=/dev/null",
    "wipefs"
]

# 4. 恶意代码与系统瘫痪 (Malicious code)
MALICIOUS_KEYWORDS = [
    ":(){ :|:& };:", "fork bomb", "提权", "删库跑路", "drop table", "drop database"
]

# 5. 严重安全防护破坏 (Security bypassing/Tampering configs)
SECURITY_BYPASS_KEYWORDS = [
    "禁用防火墙", "关闭防火墙", "停止防火墙", "清空防火墙", 
    "iptables -F", "iptables --flush", "ufw disable", "systemctl stop firewalld", "systemctl disable firewalld",
    "关闭selinux", "setenforce 0", 
    "开放所有端口", "清空安全组",
    "修改sshd_config", "允许root空密码", "清空被控端密钥", "删除/etc/passwd", "删除/etc/shadow"
]

# 6. 大范围的用户权限与越权变更 (Broad privilege escalation)
PRIVILEGE_ESCALATION_KEYWORDS = [
    "给所有人最高权限", "把所有人设为root", "将所有人加入root组", "清空所有用户密码", "删除管理员密码",
    "chmod -R 777 /", "chmod 777 -R /", "chmod -R 777 /etc", "chmod -R 777 /usr",
    "chown -R nobody", "chown -R root /", "visudo免密", "配置sudo无密码"
]

ALL_DANGEROUS_PATTERNS = (
    SHUTDOWN_KEYWORDS + 
    DESTRUCTIVE_FILE_KEYWORDS + 
    DEK_FORMAT_KEYWORDS + 
    MALICIOUS_KEYWORDS + 
    SECURITY_BYPASS_KEYWORDS +
    PRIVILEGE_ESCALATION_KEYWORDS
)

def matches_high_risk_intent(user_input: str) -> tuple:
    """
    检查用户的输入是否包含高危自然语言或命令行模式。
    返回: (是否为高危指令, 命中的危险模式字符串)
    """
    if not user_input:
        return False, None
        
    user_input_lower = user_input.lower()
    
    for pattern in ALL_DANGEROUS_PATTERNS:
        # 部分命令可能是作为参数，因此直接检查子串匹配
        # 如果将来需要精确的词汇边界，可用正则或前缀/后缀界定
        if pattern.lower() in user_input_lower:
            return True, pattern
            
    return False, None
