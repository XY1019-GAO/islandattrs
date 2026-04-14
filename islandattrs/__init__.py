"""
islandattrs - 岛屿属性计算工具包
版本：0.1.2
功能：
1. 计算岛屿多种地理属性（DM、SDM、DN5、DNL、NI、B1/B3/B5等）
2. 内置71个群岛+7大洲+中国沿海岛屿的已计算结果，支持ID一键调取
3. 支持全岛屿/目标岛屿双模式，可灵活配置计算范围
4. 完全符合岛屿生物地理学学术定义，计算结果可直接用于论文研究
仅托管于GitHub，暂不上传PyPI
"""

# 从core.py导入核心计算类与便捷函数
from .core import (
    IslandAttributeCalculator,
    calculate_island_attributes
)

# 从data_loader.py导入内置数据集调取函数
from .data_loader import (
    list_built_in_datasets,
    load_built_in_dataset,
    load_archipelago_info,
    search_archipelago_info
)

# 包元数据
__version__ = "0.1.2"
__author__ = "Island Attribute Calculator"
__all__ = [
    "IslandAttributeCalculator",
    "calculate_island_attributes",
    "list_built_in_datasets",
    "load_built_in_dataset",
    "load_archipelago_info",
    "search_archipelago_info",
]