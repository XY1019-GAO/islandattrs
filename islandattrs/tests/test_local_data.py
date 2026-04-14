"""
测试3：islandattrs用户本地数据计算功能
测试场景：用户安装包后，使用自己本地的岛屿/海岸线/目标岛屿数据进行计算
用户仅需修改下方「用户本地数据配置」区域的路径，其余无需修改
"""
from islandattrs import calculate_island_attributes

print("="*60)
print("开始测试：islandattrs用户本地数据计算功能")
print("="*60)

# ====================== 用户本地数据配置（仅需修改此处）======================
# 请将下方路径替换为你本地的实际文件路径，路径前加r避免转义字符报错
local_config = {
    "islands_path": r"E:\islandattrs_test\input\Azorespoly.shp",  # 本地岛屿shp文件路径
    "coastline_path": r"E:\islandattrs_test\input\C_shoreline.shp",  # 本地海岸线shp文件路径
    "target_file_path": r"E:\islandattrs_test\input\target_islands.xlsx",  # 本地目标岛屿xlsx路径
    "target_id_column": "ID",  # 目标岛屿表格中的ID列名
    "output_dir": r"E:\islandattrs\local_test_output",  # 结果输出目录
}
# ==============================================================================

# 1. 打印配置信息
print("\n1. 本地数据配置：")
for key, value in local_config.items():
    print(f"   {key}: {value}")

# 2. 一站式计算所有属性
print("\n2. 开始执行全流程计算（加载→计算→保存）...")
calculator = calculate_island_attributes(
    coastline_path=local_config["coastline_path"],
    islands_path=local_config["islands_path"],
    target_file_path=local_config["target_file_path"],
    target_id_column=local_config["target_id_column"],
    output_dir=local_config["output_dir"],
    attributes="all",
    sdm_use_target_only=True,
    ni_use_target_only=False,
    ni_prime_use_target_only=False,
    save_formats=["excel", "csv", "shapefile"],
    save_centroids=True,
    save_all_islands=False
)

# 3. 输出测试总结
print("\n" + "="*60)
print("✅ 用户本地数据计算功能全部测试通过！")
print(f"   已计算属性：{sorted(calculator.get_calculated_attributes())}")
print(f"   计算模式：{'目标岛屿模式' if calculator.is_target_mode else '全岛屿模式'}")
if calculator.is_target_mode:
    print(f"   有效目标岛屿数量：{len(calculator.target_island_ids) if calculator.target_island_ids else 0}")
print(f"   结果保存路径：{local_config['output_dir']}")
print("="*60) 
