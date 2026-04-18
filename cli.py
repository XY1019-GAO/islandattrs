import argparse
from .core import calculate_attributes
from .data_loader import list_built_in_datasets, load_archipelago_info

def main():
    parser = argparse.ArgumentParser(
        description="islandattrs - 岛屿生物地理学地理属性计算工具包"
    )
    parser.add_argument("-v", "--version", action="version", version="islandattrs 0.1.2")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有内置数据集")
    parser.add_argument("-t", "--test", action="store_true", help="运行内置测试")
    args = parser.parse_args()

    if args.list:
        print("\n内置数据集：")
        datasets = list_built_in_datasets()
        for d in datasets:
            print(f"- {d}")
        return

    if args.test:
        from .tests.test_built_in_datasets import run_all_tests
        run_all_tests()
        return

    parser.print_help()

if __name__ == "__main__":
    main()
