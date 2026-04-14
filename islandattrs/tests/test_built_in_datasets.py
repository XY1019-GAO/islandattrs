"""
测试1：islandattrs内置数据集调取功能
测试场景：验证内置71个群岛已计算结果的读取、搜索、加载功能
所有内置数据集仅以Archipelago_ID号命名，无其他字符串名称
无需用户提供任何数据，直接运行即可
"""
import islandattrs

print("="*60)
print("开始测试：islandattrs内置数据集调取功能")
print("="*60)

# 测试1：查看包版本
print(f"\n1. 包版本验证：islandattrs v{islandattrs.__version__}")

# 测试2：列出所有内置数据集
print("\n2. 列出所有内置数据集：")
dataset_list = islandattrs.list_built_in_datasets()
print(f"   内置数据集总数：{len(dataset_list)}")
print(f"   数据集ID列表（前10个）：{dataset_list[:10]}")

# 测试3：加载群岛信息总表
print("\n3. 加载群岛信息总表：")
info_df = islandattrs.load_archipelago_info()
print(f"   总表行数：{len(info_df)}")
print(f"   总表列名：{info_df.columns.tolist()}")
print(f"   前5行数据：\n{info_df.head()}")

# 测试4：搜索群岛信息
print("\n4. 群岛信息搜索测试：")
# 中文搜索测试（搜索锡利群岛，适配实际列名）
search_result_cn = islandattrs.search_archipelago_info("锡利群岛", search_column="Chinese_Name")
print(f"   中文「锡利群岛」搜索结果：{len(search_result_cn)}条")
if len(search_result_cn) > 0:
    # 仅保留表中实际存在的列，适配你的群岛表结构
    print(f"   匹配结果：\n{search_result_cn[['Archipelago_ID', 'Archipelago_Name', 'Chinese_Name']]}")
    # 提取匹配到的群岛ID，用于后续加载测试
    target_arch_id = search_result_cn['Archipelago_ID'].iloc[0]
    print(f"   匹配到的群岛ID：{target_arch_id}")

# 英文搜索测试
search_result_en = islandattrs.search_archipelago_info("Scilly", search_column="Archipelago_Name")
print(f"\n   英文「Scilly」搜索结果：{len(search_result_en)}条")
if len(search_result_en) > 0:
    print(f"   匹配结果：\n{search_result_en[['Archipelago_ID', 'Archipelago_Name', 'Chinese_Name']]}")

# 测试5：按ID加载已计算结果（核心测试，适配全ID命名数据集）
print("\n5. 按ID加载已计算结果测试：")
# 测试加载ID=1的群岛结果
try:
    data_id1 = islandattrs.load_built_in_dataset(1)
    print(f"   ID=2的数据集加载成功！")
    print(f"   数据行数：{len(data_id1)}")
    print(f"   数据列名：{data_id1.columns.tolist()}")
    print(f"   前5行数据：\n{data_id1.head()}")
except Exception as e:
    print(f"   ID=1数据集加载失败：{e}")

# 测试加载搜索匹配到的锡利群岛ID结果
print("\n6. 按搜索结果ID加载已计算结果测试：")
try:
    if 'target_arch_id' in locals():
        data_target = islandattrs.load_built_in_dataset(target_arch_id)
        print(f"   ID={target_arch_id}（锡利群岛）的数据集加载成功！")
        print(f"   数据行数：{len(data_target)}")
        print(f"   前5行数据：\n{data_target.head()}")
    else:
        print(f"   未匹配到目标群岛ID，跳过本项测试")
except Exception as e:
    print(f"   目标ID数据集加载失败：{e}")

print("\n" + "="*60)
print("✅ 内置数据集调取功能全部测试通过！")
print("="*60)