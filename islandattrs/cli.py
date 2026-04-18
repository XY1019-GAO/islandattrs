# -*- coding: utf-8 -*-
import sys
import os

def main():
    # 先处理内置数据调取命令
    if "--list-archi" in sys.argv or "--get-result" in sys.argv:
        import argparse
        from .data_loader import load_archipelago_info, load_built_in_dataset
        
        parser = argparse.ArgumentParser()
        parser.add_argument("--list-archi", action="store_true")
        parser.add_argument("--get-result", type=str)
        parser.add_argument("-o", "--output", type=str)
        args, _ = parser.parse_known_args()
        
        if args.list_archi:
            try:
                df = load_archipelago_info()
                print(f"\n📚 内置群岛名录（共{len(df)}个）")
                print(df.to_string(index=False))
                if args.output:
                    df.to_excel(args.output, index=False)
                    print(f"\n✅ 已保存至：{args.output}")
            except Exception as e:
                print(f"❌ 失败：{e}")
            sys.exit(0)
        
        if args.get_result:
            try:
                df = load_built_in_dataset(args.get_result)
                print(f"\n📊 群岛ID【{args.get_result}】结果（{len(df)}个岛屿）")
                print(df.head(10))
                if args.output:
                    df.to_excel(args.output, index=False)
                    print(f"\n✅ 已保存至：{args.output}")
            except Exception as e:
                print(f"❌ 失败：{e}")
            sys.exit(0)

    # 所有其他命令直接转发给core.py的main函数
    from .core import main as core_main
    core_main()

# 保证直接运行cli.py也能生效
if __name__ == "__main__":
    main()