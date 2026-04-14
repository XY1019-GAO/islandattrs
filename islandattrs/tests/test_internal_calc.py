"""
测试2：islandattrs包内部数据计算功能
测试场景：使用包内自带的示例测试数据，验证岛屿属性全流程计算功能
无需用户提供任何数据，直接运行即可
"""
import os
from islandattrs import IslandAttributeCalculator

print("="*60)
print("开始测试：islandattrs包内部数据计算功能")
print("="*60)

# 1. 自动定位包内测试数据路径（无需手动修改）
package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
test_data_dir = os.path.join(package_root, "data", "test_data")
output_dir = os.path.join(test_data_dir, "calc_test_output")

# 2. 定义包内数据路径
islands_path = os.path.join(test_data_dir, "Azorespoly.shp")
coastline_path = os.path.join(test_data_dir, "C_shoreline.shp")
target_file_path = os.path.join(test_data_dir, "target_islands.xlsx")

# 打印路径信息
print(f"\n1. 包内测试数据路径：")
print(f"   岛屿图层：{islands_path}")
print(f"   海岸线图层：{coastline_path}")
print(f"   目标岛屿表格：{target_file_path}")
print(f"   结果输出目录：{output_dir}")

# 3. 校验文件是否存在
file_check = [
    ("岛屿图层", islands_path),
    ("海岸线图层", coastline_path),
    ("目标岛屿表格", target_file_path)
]
for name, path in file_check:
    if not os.path.exists(path):
        print(f"❌ {name}文件不存在：{path}")
        exit()
print("\n2. 所有测试文件校验通过！")

# 4. 初始化计算器（启用目标岛屿模式）
print("\n3. 初始化岛屿属性计算器...")
calculator = IslandAttributeCalculator(
    coastline_path=coastline_path,
    islands_path=islands_path,
    target_file_path=target_file_path,
    target_id_column="ID",
    output_dir=output_dir
)

# 5. 计算所有属性
print("\n4. 开始计算所有岛屿属性（SDM仅基于目标岛屿，NI基于全岛屿）...")
calc_success = calculator.calculate_all_attributes(
    sdm_use_target_only=True,
    ni_use_target_only=False,
    ni_prime_use_target_only=False
)

# 6. 保存结果
if calc_success:
    print("\n5. 计算完成，正在保存结果...")
    calculator.save_results(
        output_format=["excel", "csv", "shapefile"],
        filename_prefix="internal_calc_test_results",
        save_centroids=True,
        save_all_islands=False
    )

    # 打印测试总结
    print("\n" + "="*60)
    print("✅ 包内部数据计算功能全部测试通过！")
    print(f"   已计算属性：{sorted(calculator.get_calculated_attributes())}")
    print(f"   有效目标岛屿数量：{len(calculator.target_island_ids) if calculator.target_island_ids else 0}")
    print(f"   结果保存路径：{output_dir}")
    print("="*60)
else:
    print("\n❌ 包内部数据计算测试失败，请检查上方错误日志")
    exit() 
