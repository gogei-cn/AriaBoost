#!/usr/bin/env python3
"""
AriaBoost 发布脚本
功能：提交代码 → 推送 → 打 tag → 推送 tag
GitHub Actions 会自动构建并创建 Release
"""

import sys
import subprocess
import argparse

def run_cmd(cmd, check=True):
    print(f"🔧 {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"❌ 失败: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()

def main():
    parser = argparse.ArgumentParser(description="AriaBoost Git 推送脚本")
    parser.add_argument("version", help="版本号，如 1.0.0")
    parser.add_argument("--msg", help="提交信息", default="")
    args = parser.parse_args()

    tag = f"v{args.version}"
    # 如果没有提供自定义消息，使用包含 tag 的默认消息
    msg = args.msg or f"Release {tag}"

    print(f"📦 准备发布: {tag}")

    # 验证版本号格式（建议 x.y.z）
    if len(args.version.split(".")) != 3:
        print("⚠️ 建议使用 x.y.z 格式，如 1.0.0")

    # 1. 确保在 main 分支
    branch = run_cmd("git branch --show-current")
    if branch != "main":
        print(f"⚠️ 当前在 {branch}，建议切换到 main")
        if input("继续？(y/N): ").lower() != "y":
            sys.exit(0)

    # 2. 提交变更（使用动态消息）
    run_cmd("git add .")
    status = run_cmd("git status --porcelain", check=False)
    if status:
        run_cmd(f'git commit -m "{msg}"')
    else:
        print("⚠️ 没有变更需要提交")

    # 3. 推送代码
    run_cmd("git push origin main")

    # 4. 检查 tag 是否已存在（本地）
    local_tag = run_cmd(f"git tag -l {tag}", check=False)
    if local_tag:
        print(f"⚠️ 本地 Tag {tag} 已存在，删除...")
        run_cmd(f"git tag -d {tag}")

    # 5. 检查远程 tag 是否存在，如果存在则删除
    remote_tags = run_cmd(f"git ls-remote --tags origin {tag}", check=False)
    if remote_tags:
        print(f"⚠️ 远程 Tag {tag} 已存在，删除...")
        run_cmd(f"git push origin :refs/tags/{tag}")

    # 6. 创建并推送 tag（使用动态消息）
    run_cmd(f'git tag -a {tag} -m "{msg}"')
    run_cmd(f"git push origin {tag}")

    print(f"✅ 发布完成！")
    print(f"📝 GitHub Actions 正在构建: https://github.com/gogei-cn/AriaBoost/actions")
    print(f"📦 Release 将在此创建: https://github.com/gogei-cn/AriaBoost/releases")

if __name__ == "__main__":
    main()