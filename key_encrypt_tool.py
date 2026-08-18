#!/usr/bin/env python3
"""
API Key AES-256-CBC 加密工具

用法：
    python key_encrypt_tool.py encrypt <api-key>      加密 API Key
    python key_encrypt_tool.py decrypt <encrypted>     解密密文
    python key_encrypt_tool.py test                    运行自测
    python key_encrypt_tool.py encrypt-default          加密默认 API Key

注意：加密结果与当前机器特征（hostname + username）绑定。
      在不同机器上加密的结果无法互相解密。
"""
import sys
import platform
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.encryption import AesEncryptionService

# 用户提供的 API Key
DEFAULT_API_KEY = "d7cec952aa864c9ba3858b1cb609f427.ryJ3FOH9MrvIKMsK"


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * min(len(key) - 8, 20) + key[-4:]


def get_user_display():
    try:
        return os.getlogin()
    except OSError:
        return os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"


def handle_encrypt(svc: AesEncryptionService, api_key: str):
    print(f"机器信息: {platform.node()}\\{get_user_display()}")
    print(f"原始 API Key: {mask_key(api_key)}")
    print(f"Key 长度: {len(api_key)} 字符")
    print()

    print("正在加密 (PBKDF2 600,000 次迭代)...")
    encrypted = svc.encrypt(api_key)

    print()
    print("=== 加密成功 ===")
    print("Base64 密文:")
    print(encrypted)
    print()

    # 验证解密
    print("正在验证解密...")
    decrypted = svc.decrypt(encrypted)
    if decrypted == api_key:
        print(f"验证通过! 解密结果: {mask_key(decrypted)}")
    else:
        print("验证失败! 解密结果不匹配!")
        sys.exit(1)

    print()
    print("请将上述加密字符串配置到 credentials.json 或通过设置页面保存。")
    return encrypted


def handle_decrypt(svc: AesEncryptionService, encrypted: str):
    print(f"机器信息: {platform.node()}\\{get_user_display()}")
    print()

    try:
        decrypted = svc.decrypt(encrypted)
        print("=== 解密成功 ===")
        print(f"解密结果: {mask_key(decrypted)}")
    except Exception as e:
        print(f"解密失败: {e}")
        print("可能原因：")
        print("  1. 密文数据已损坏")
        print("  2. 当前机器/用户与加密时不同")
        print("  3. 密文格式不正确")
        sys.exit(1)


def handle_test(svc: AesEncryptionService):
    print("=== AES 加密服务自测 ===")
    print(f"机器: {platform.node()}\\{get_user_display()}")
    print()

    test_cases = [
        DEFAULT_API_KEY,
        "short-key",
        "中文测试密钥_!@#$%^&*()",
        "A" * 1000,
    ]

    all_passed = True
    for tc in test_cases:
        display = tc[:20] + "..." + tc[-10:] if len(tc) > 40 else tc
        try:
            enc = svc.encrypt(tc)
            dec = svc.decrypt(enc)
            if dec == tc:
                print(f"  [通过] {display}")
            else:
                print(f"  [失败] {display} - 解密结果不匹配")
                all_passed = False
        except Exception as e:
            print(f"  [异常] {display} - {e}")
            all_passed = False

    print()
    print("全部测试通过!" if all_passed else "存在失败的测试用例!")
    return all_passed


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    svc = AesEncryptionService()
    cmd = sys.argv[1].lower()

    if cmd == "encrypt":
        if len(sys.argv) < 3:
            print("错误：请提供要加密的 API Key")
            print("用法：python key_encrypt_tool.py encrypt <api-key>")
            sys.exit(1)
        handle_encrypt(svc, sys.argv[2])

    elif cmd == "encrypt-default":
        handle_encrypt(svc, DEFAULT_API_KEY)

    elif cmd == "decrypt":
        if len(sys.argv) < 3:
            print("错误：请提供要解密的密文")
            print("用法：python key_encrypt_tool.py decrypt <encrypted-base64>")
            sys.exit(1)
        handle_decrypt(svc, sys.argv[2])

    elif cmd == "test":
        ok = handle_test(svc)
        sys.exit(0 if ok else 1)

    else:
        print(f"未知命令: {cmd}")
        print_usage()
        sys.exit(1)


def print_usage():
    print("考试智能广播系统 - API Key 加密工具 (Python 版)")
    print()
    print("用法：")
    print("  python key_encrypt_tool.py encrypt <api-key>       加密 API Key")
    print("  python key_encrypt_tool.py encrypt-default          加密内置默认 API Key")
    print("  python key_encrypt_tool.py decrypt <encrypted>     解密已加密的密文")
    print("  python key_encrypt_tool.py test                    运行自测")
    print()
    print("注意：加密结果与当前机器（hostname + username）绑定。")


if __name__ == "__main__":
    main()
