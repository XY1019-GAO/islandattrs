"""
内置数据集加载模块
功能：调取包内71个群岛的已计算结果，支持搜索、筛选
适配场景：所有内置数据集仅以Archipelago_ID号命名，无其他字符串名称
"""
import os
import pandas as pd
from importlib.resources import files

def list_built_in_datasets():
    """
    列出所有内置的已计算群岛数据集
    返回：排序后的数据集ID列表（字符串格式）
    """
    try:
        # 定位包内内置结果目录
        results_dir = files("islandattrs.data").joinpath("built_in_results")
        if not results_dir.exists():
            print("警告：内置数据集目录不存在")
            return []
        
        # 筛选所有xlsx/csv结果文件，提取ID（文件名不含后缀）
        dataset_files = [
            f for f in os.listdir(results_dir)
            if f.endswith(('.xlsx', '.xls', '.csv'))
        ]
        # 提取ID并按数字排序
        dataset_ids = [os.path.splitext(f)[0] for f in dataset_files]
        return sorted(dataset_ids, key=lambda x: int(x) if x.isdigit() else x)
    
    except Exception as e:
        print(f"读取内置数据集列表失败：{e}")
        return []

def load_built_in_dataset(dataset_identifier):
    """
    加载指定的内置已计算结果表
    适配说明：所有内置数据集仅以Archipelago_ID号命名，仅支持传入数字/字符串格式的ID
    :param dataset_identifier: 群岛唯一ID（支持数字/字符串格式，如1、2、"3"，对应Archipelago_ID）
    :return: pandas.DataFrame，对应群岛的岛屿属性计算结果
    """
    # 定位内置结果目录
    results_dir = files("islandattrs.data").joinpath("built_in_results")
    # 支持的文件格式
    support_ext = ['.xlsx', '.xls', '.csv']
    target_file = None

    # 强制校验并转换为ID格式
    try:
        arch_id = str(int(dataset_identifier))
        # 按ID查找对应文件
        for ext in support_ext:
            candidate_path = results_dir.joinpath(f"{arch_id}{ext}")
            if candidate_path.exists():
                target_file = candidate_path
                break
    except (ValueError, TypeError):
        # 非数字格式直接抛出异常，明确仅支持ID加载
        raise ValueError(
            f"无效的数据集标识：{dataset_identifier}\n"
            "当前所有内置数据集仅以Archipelago_ID号命名，仅支持传入数字格式的ID\n"
            f"可用数据集ID列表：{list_built_in_datasets()}"
        )

    # 未找到文件，抛出异常
    if target_file is None:
        raise FileNotFoundError(
            f"未找到ID为{arch_id}的内置数据集\n"
            f"可用数据集ID列表：{list_built_in_datasets()}\n"
            "请确认对应ID的结果文件已放入 built_in_results 目录"
        )

    # 读取文件
    try:
        if str(target_file).endswith('.csv'):
            return pd.read_csv(target_file, encoding='utf-8-sig')
        else:
            return pd.read_excel(target_file)
    except Exception as e:
        raise RuntimeError(f"数据集读取失败：{e}")

def load_archipelago_info():
    """
    加载群岛信息总表，包含所有内置数据集的介绍、ID、名称等信息
    完全适配你的 archipelago_info.xlsx 实际列名
    :return: pandas.DataFrame，群岛完整信息表
    """
    info_file = files("islandattrs.data").joinpath("archipelago_info.xlsx")
    
    if not info_file.exists():
        raise FileNotFoundError(
            f"未找到群岛信息总表：{info_file}\n"
            "请确认archipelago_info.xlsx已放入islandattrs/data目录"
        )

    try:
        info_df = pd.read_excel(info_file)
        # 数据清洗，适配你的表实际字段
        info_df = info_df.fillna({
            "Note": "无额外说明",
            "Island_Count": 0,
            "Associated archipelago": "无关联群岛"
        })
        # 列名去空格，避免隐藏空格导致的列名匹配失败
        info_df.columns = [col.strip() for col in info_df.columns]
        return info_df
    except Exception as e:
        raise RuntimeError(f"群岛信息表读取失败：{e}")

def search_archipelago_info(keyword, search_column="Chinese_Name"):
    """
    按关键词模糊搜索群岛信息
    :param keyword: 搜索关键词（支持中英文，如"锡利群岛"、"Scilly"、"巴哈马"）
    :param search_column: 搜索列，可选值（完全适配你的表格）：
        Archipelago_Name（英文名称）、Chinese_Name（中文名称）、
        Associated archipelago（关联群岛）、Note（备注信息）
    :return: pandas.DataFrame，匹配的群岛信息
    """
    # 加载总表
    info_df = load_archipelago_info()
    # 校验搜索列，仅保留表格中真实存在的列
    valid_columns = ["Archipelago_Name", "Chinese_Name", "Associated archipelago", "Note"]
    if search_column not in valid_columns:
        raise ValueError(
            f"无效的搜索列：{search_column}\n"
            f"可选搜索列：{valid_columns}"
        )

    # 模糊匹配（不区分大小写，适配中英文）
    keyword = str(keyword).lower().strip()
    match_result = info_df[
        info_df[search_column].astype(str).str.lower().str.contains(keyword, na=False)
    ]

    if len(match_result) == 0:
        print(f"未找到包含关键词「{keyword}」的群岛信息（搜索列：{search_column}）")
        return pd.DataFrame(columns=info_df.columns)
    
    return match_result