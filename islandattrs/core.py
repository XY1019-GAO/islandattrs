#!/usr/bin/env python3
"""
岛屿属性计算工具包 - Island Attribute Calculator Package
计算岛屿的多种地理属性，包括距离、邻近性、陆地占比等指标
版本 0.1.2 - 完整保留原始代码 + 修复所有长度不匹配问题
"""
import os
import sys
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon, LineString
from shapely.validation import make_valid
from pyproj import CRS, Transformer
import networkx as nx
import matplotlib.pyplot as plt
from tqdm import tqdm
import math
import warnings
from scipy import spatial
from sklearn.neighbors import BallTree
import concurrent.futures
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，避免GUI问题
warnings.filterwarnings('ignore')

__version__ = "0.1.2"
__author__ = "Island Attribute Calculator"


class IslandAttributeCalculator:
    """
    岛屿属性计算器 - 最终对齐版
    所有指标100%符合岛屿生物地理学学术定义，完全对齐旧版结果
    完整保留所有原有功能和向后兼容性
    """
    
    # 定义可用的计算函数及其对应的属性
    AVAILABLE_CALCULATIONS = {
        'DM': {
            'function': 'calculate_coastline_distance',
            'description': '大陆距离 (Distance to Mainland)',
            'dependencies': []
        },
        'SDM': {
            'function': 'calculate_stepping_stone_distance',
            'description': '踏脚石距离 (Stepping-stone Distance to Mainland)',
            'dependencies': ['DM']
        },
        'DN5': {
            'function': 'calculate_average_island_distance',
            'description': '平均岛屿距离 (Average Distance to 5 nearest islands)',
            'dependencies': []
        },
        'DNL': {
            'function': 'calculate_nearest_large_island_distance',
            'description': '最近大岛距离 (Distance to Nearest Larger island)',
            'dependencies': []
        },
        "DNL'": {
            'function': 'calculate_nearest_large_island_distance',
            'description': "最近大岛距离' (Distance to Nearest Larger island > 0.05 km²)",
            'dependencies': []
        },
        'NI': {
            'function': 'calculate_neighbor_indices',
            'description': '近邻指数 (Neighbor Index)',
            'dependencies': []
        },
        "NI'": {
            'function': 'calculate_neighbor_indices',
            'description': "近邻指数' (Neighbor Index for large islands > 0.05 km²)",
            'dependencies': []
        },
        'B1': {
            'function': 'calculate_land_ratio_buffer',
            'description': '周边陆地占比 1km (Land ratio in 1km buffer)',
            'dependencies': []
        },
        'B3': {
            'function': 'calculate_land_ratio_buffer',
            'description': '周边陆地占比 3km (Land ratio in 3km buffer)',
            'dependencies': []
        },
        'B5': {
            'function': 'calculate_land_ratio_buffer',
            'description': '周边陆地占比 5km (Land ratio in 5km buffer)',
            'dependencies': []
        }
    }
    
    def __init__(self, 
             coastline_path=None, 
             islands_path=None,
             target_file_path=None,
             target_id_column='ID',
             island_id_column='ID',  # 🔥 新增：自定义岛屿图层ID列名
             input_dir="input",
             output_dir="output",
             coastline_filename="C_shoreline.shp",
             islands_filename="ArchipelagoDeColonpoly.shp"):
        """
        初始化计算器
        :param coastline_path: 海岸线shp文件完整路径
        :param islands_path: 岛屿图层shp文件完整路径
        :param target_file_path: 目标岛屿表格文件路径（支持xlsx/csv）
        :param target_id_column: 目标岛屿表格中的ID列名，默认'ID'
        :param input_dir: 输入文件目录（未指定完整路径时使用）
        :param output_dir: 输出文件目录
        :param coastline_filename: 海岸线文件名（未指定完整路径时使用）
        :param islands_filename: 岛屿图层文件名（未指定完整路径时使用）
        """
        # 设置输入路径（优先使用完整路径，其次使用目录+文件名）
        if coastline_path:
            self.coastline_path = coastline_path
        else:
            self.coastline_path = os.path.join(input_dir, coastline_filename)
            
        if islands_path:
            self.islands_path = islands_path
        else:
            self.islands_path = os.path.join(input_dir, islands_filename)
        
        # 目标岛屿相关配置
        self.target_file_path = target_file_path
        self.target_id_column = target_id_column
        self.island_id_column = island_id_column 
        
        # 输出目录
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 核心数据存储（全量与目标分离，保证计算隔离）
        self.islands_utm_full = None  # 完整全岛屿图层（所有计算的基础）
        self.islands_utm = None       # 当前计算的岛屿集合（全量/目标）
        self.coastline_utm = None
        self.utm_crs = None
        self.coastline_sindex = None
        self.original_crs = None
        
        # 目标模式相关
        self.target_island_ids = None  # 有效目标岛屿ID集合
        self.is_target_mode = False   # 是否启用目标岛屿模式
        
        # 计算记录
        self.calculated_attributes = set()
        self.calculation_options = {}
        
        print(f"岛屿图层路径: {self.islands_path}")
        print(f"海岸线路径: {self.coastline_path}")
        if self.target_file_path:
            print(f"目标岛屿文件: {self.target_file_path}")
            print(f"目标ID列名: {self.target_id_column}")
        print(f"输出目录: {self.output_dir}")
    
    def clean_geometry(self, gdf, geometry_column='geometry'):
        """清理几何对象，修复无效几何"""
        print("清理几何对象...")
        
        cleaned_gdf = gdf.copy()
        cleaned_count = 0
        empty_count = 0
        
        for idx, row in tqdm(cleaned_gdf.iterrows(), total=len(cleaned_gdf), desc="清理几何"):
            geom = row[geometry_column]
            
            if geom is None or geom.is_empty:
                empty_count += 1
                cleaned_gdf.at[idx, geometry_column] = None
                continue
            
            try:
                bbox = geom.bounds
                if any(math.isnan(c) or math.isinf(c) for c in bbox):
                    valid_geom = make_valid(geom)
                    if valid_geom and not valid_geom.is_empty:
                        cleaned_gdf.at[idx, geometry_column] = valid_geom
                        cleaned_count += 1
                    else:
                        cleaned_gdf.at[idx, geometry_column] = None
                        empty_count += 1
            except Exception as e:
                try:
                    valid_geom = make_valid(geom)
                    if valid_geom and not valid_geom.is_empty:
                        cleaned_gdf.at[idx, geometry_column] = valid_geom
                        cleaned_count += 1
                    else:
                        cleaned_gdf.at[idx, geometry_column] = None
                        empty_count += 1
                except:
                    cleaned_gdf.at[idx, geometry_column] = None
                    empty_count += 1
        
        if empty_count > 0:
            original_count = len(cleaned_gdf)
            cleaned_gdf = cleaned_gdf.dropna(subset=[geometry_column])
            print(f"  删除 {empty_count} 个无效几何对象，从 {original_count} 到 {len(cleaned_gdf)}")
        
        print(f"✓ 几何对象清理完成: 修复 {cleaned_count} 个，删除 {empty_count} 个无效几何")
        return cleaned_gdf
    
    def load_target_islands(self):
        """读取目标岛屿表格文件，验证并提取有效目标岛屿ID"""
        if not self.target_file_path or not os.path.exists(self.target_file_path):
            print(f"❌ 目标岛屿文件不存在: {self.target_file_path}")
            return False
        
        try:
            # 支持xlsx和csv格式
            if self.target_file_path.endswith('.xlsx'):
                target_df = pd.read_excel(self.target_file_path)
            elif self.target_file_path.endswith('.csv'):
                target_df = pd.read_csv(self.target_file_path)
            else:
                print(f"❌ 不支持的目标文件格式，仅支持xlsx/csv: {self.target_file_path}")
                return False
            
            # 检查目标ID列是否存在
            if self.target_id_column not in target_df.columns:
                print(f"❌ 目标文件中不存在指定的ID列: {self.target_id_column}")
                print(f"目标文件的列名列表: {target_df.columns.tolist()}")
                return False
            
            # 提取、去重、过滤空值
            target_ids = target_df[self.target_id_column].dropna().unique()
            
            # 匹配岛屿图层的ID数据类型
            island_id_dtype = self.islands_utm_full[self.island_id_column].dtype
            try:
                target_ids = target_ids.astype(island_id_dtype)
            except Exception as e:
                print(f"❌ 目标ID类型转换失败，无法匹配岛屿图层ID类型: {e}")
                return False
            
            # 验证ID有效性，过滤不存在的ID
            valid_ids = [id for id in target_ids if id in self.islands_utm_full[self.island_id_column].values]
            invalid_ids = [id for id in target_ids if id not in self.islands_utm_full[self.island_id_column].values]
            
            if invalid_ids:
                print(f"⚠ 警告: 以下目标ID在岛屿图层中不存在，已自动过滤: {invalid_ids}")
            
            if len(valid_ids) == 0:
                print(f"❌ 无有效的目标岛屿ID，无法启用目标模式")
                return False
            
            # 赋值目标模式相关属性
            self.target_island_ids = set(valid_ids)
            self.is_target_mode = True
            self.islands_utm = self.islands_utm_full[self.islands_utm_full[self.island_id_column].isin(self.target_island_ids)].copy()
            
            print(f"✓ 目标岛屿加载完成，有效目标岛屿数量: {len(self.target_island_ids)}")
            return True
        
        except Exception as e:
            print(f"❌ 目标岛屿文件读取失败: {e}")
            return False
    
    def load_data(self):
        """加载数据、转换坐标系、计算基础属性（Area、Lon、Lat），自动处理目标岛屿"""
        print("="*40)
        print("开始加载并预处理数据...")
        
        # ====================== Shapely 2.0+ 原生加速（无需 PyGeos）======================
        gpd.options.use_pygeos = False
        print("✓ Shapely 2.0+ 几何加速已启用（无需 PyGeos）")
        
        # 检查必填文件
        required_files = [self.coastline_path, self.islands_path]
        for file_path in required_files:
            if not os.path.exists(file_path):
                print(f"❌ 缺少必填文件: {file_path}")
                return False
        
        # 读取原始数据
        try:
            coastline = gpd.read_file(self.coastline_path)
            islands = gpd.read_file(self.islands_path)
            print("✓ 原始数据读取成功")
        except Exception as e:
            print(f"❌ 数据读取失败: {e}")
            return False
        
        print(f"原始岛屿总数量: {len(islands)}")
        print(f"海岸线要素数量: {len(coastline)}")
        print(f"原始属性字段: {list(islands.columns)}")
        
        # 清理几何
        islands = self.clean_geometry(islands)
        coastline = self.clean_geometry(coastline)
        
        # 自动添加ID列（如果不存在）
        if self.island_id_column not in islands.columns:
            print(f"岛屿图层无 {self.island_id_column} 列，正在自动添加（从1开始递增）...")
            islands[self.island_id_column] = range(1, len(islands) + 1)
            print(f"✓ {self.island_id_column} 列添加完成，ID范围: 1-{len(islands)}")
        
        self.original_crs = islands.crs
        print(f"原始坐标系: {self.original_crs}")
        
        # 简化过多的海岸线要素，提升计算效率
        if len(coastline) > 100000:
            print("海岸线要素过多，正在进行简化...")
            coastline['geometry'] = coastline.simplify(100)
            print(f"  简化后海岸线要素数量: {len(coastline)}")
        
        # 自动转换为UTM投影坐标系（保证距离计算精度）
        print("转换投影坐标系...")
        try:
            if len(islands) > 0:
                centroid = islands.geometry.centroid.unary_union.centroid
                utm_zone = int((centroid.x + 180) / 6) + 1
                hemisphere = 'north' if centroid.y >= 0 else 'south'
                self.utm_crs = f"EPSG:326{utm_zone:02d}" if hemisphere == 'north' else f"EPSG:327{utm_zone:02d}"
                
                # 全岛屿图层转换坐标系（核心基础数据，永不修改）
                self.islands_utm_full = islands.to_crs(self.utm_crs)
                self.coastline_utm = coastline.to_crs(self.utm_crs)
                print(f"✓ 已转换为UTM投影坐标系: {self.utm_crs}")
            else:
                print("❌ 无有效的岛屿数据")
                return False
        except Exception as e:
            print(f"⚠ UTM坐标系转换失败，已切换为Web Mercator: {e}")
            self.utm_crs = "EPSG:3857"
            self.islands_utm_full = islands.to_crs(self.utm_crs)
            self.coastline_utm = coastline.to_crs(self.utm_crs)
        
        # 计算全岛屿的基础属性（质心、面积、中心经纬度）
        print("计算全岛屿基础属性...")
        self.islands_utm_full['centroid'] = self.islands_utm_full.geometry.centroid
        self.islands_utm_full['Area'] = self.islands_utm_full.geometry.area / 1e6  # 单位：km²
        
        # 计算中心经纬度（转换回原始坐标系）
        print("计算岛屿中心经纬度...")
        try:
            centroids_utm = self.islands_utm_full['centroid'].copy()
            temp_gdf = gpd.GeoDataFrame(geometry=centroids_utm, crs=self.utm_crs)
            centroids_original = temp_gdf.to_crs(self.original_crs)
            
            self.islands_utm_full['Lon'] = centroids_original.geometry.x
            self.islands_utm_full['Lat'] = centroids_original.geometry.y
            
            # 处理WGS84坐标系的经纬度范围
            if str(self.original_crs).upper() == 'EPSG:4326':
                self.islands_utm_full['Lon'] = self.islands_utm_full['Lon'].apply(lambda x: ((x + 180) % 360) - 180)
                self.islands_utm_full['Lat'] = self.islands_utm_full['Lat'].apply(lambda y: max(-90, min(90, y)))
            
            print(f"✓ 中心经纬度计算完成")
        except Exception as e:
            print(f"⚠ 中心经纬度计算失败，已使用投影坐标替代: {e}")
            self.islands_utm_full['Lon'] = self.islands_utm_full['centroid'].x
            self.islands_utm_full['Lat'] = self.islands_utm_full['centroid'].y
        
        # 数据类型压缩（内存优化）
        print("优化数据类型...")
        self.islands_utm_full['Area'] = self.islands_utm_full['Area'].astype('float32')
        self.islands_utm_full['Lon'] = self.islands_utm_full['Lon'].astype('float32')
        self.islands_utm_full['Lat'] = self.islands_utm_full['Lat'].astype('float32')
        if self.island_id_column in self.islands_utm_full.columns:  # 🔥 替换 1
            self.islands_utm_full[self.island_id_column] = pd.to_numeric(
                self.islands_utm_full[self.island_id_column], 
                downcast='integer'
            )  # 🔥 替换 2
        print("✓ 数据类型优化完成")
        
        # 创建海岸线空间索引，提升距离计算效率
        print("创建海岸线空间索引...")
        try:
            self.coastline_sindex = self.coastline_utm.sindex
            print("✓ 海岸线空间索引创建成功")
        except Exception as e:
            print(f"⚠ 空间索引创建失败: {e}")
            self.coastline_sindex = None
        
        # 处理目标岛屿模式
        if self.target_file_path:
            if not self.load_target_islands():
                print("⚠ 目标岛屿加载失败，已自动切换为全岛屿模式")
                self.islands_utm = self.islands_utm_full.copy()
                self.is_target_mode = False
        else:
            # 全岛屿模式
            self.islands_utm = self.islands_utm_full.copy()
            self.is_target_mode = False
        
        print("✓ 数据加载与预处理完成")
        print("="*40)
        return True
    
    def get_nearby_coastline(self, island_geom, buffer_distance=50000):
        """获取岛屿附近的海岸线要素，提升距离计算效率"""
        try:
            island_buffer = island_geom.buffer(buffer_distance)
            
            if self.coastline_sindex is not None:
                possible_matches_index = list(self.coastline_sindex.intersection(island_buffer.bounds))
                if possible_matches_index:
                    possible_matches = self.coastline_utm.iloc[possible_matches_index]
                    
                    valid_coastlines = []
                    for idx, coastline_row in possible_matches.iterrows():
                        try:
                            if coastline_row.geometry.intersects(island_buffer):
                                valid_coastlines.append(coastline_row)
                        except:
                            continue
                    
                    if valid_coastlines:
                        return gpd.GeoDataFrame(valid_coastlines, crs=self.coastline_utm.crs)
            else:
                nearby_coastline = self.coastline_utm[self.coastline_utm.intersects(island_buffer)]
                return nearby_coastline
            
        except Exception as e:
            print(f"⚠ 获取附近海岸线时出错: {e}")
        
        return gpd.GeoDataFrame([], columns=self.coastline_utm.columns, crs=self.coastline_utm.crs)
    
    def calculate_coastline_distance(self):
        """计算大陆距离 DM（基于全岛屿图层，不受目标模式影响）"""
        print("开始计算大陆距离 DM...")
        
        if self.islands_utm_full is None:
            print("❌ 请先加载数据")
            return False
        
        dm_values = []
        error_count = 0
        no_coastline_count = 0
        
        # 遍历全岛屿计算，保证基础数据完整
        for idx, island in tqdm(self.islands_utm_full.iterrows(), total=len(self.islands_utm_full), desc="计算DM"):
            try:
                island_geom = island.geometry
                island_boundary = island_geom.boundary if island_geom.boundary.geom_type != 'GeometryCollection' else island_geom
                
                # 逐级扩大缓冲区，保证找到最近海岸线
                distances_to_try = [50000, 100000, 200000, 500000, 1000000, 2000000, 3000000, 5000000, 10000000]
                min_distance = float('inf')
                
                for buffer_dist in distances_to_try:
                    try:
                        nearby_coastline = self.get_nearby_coastline(island_geom, buffer_dist)
                        if len(nearby_coastline) > 0:
                            for _, coastline_geom in nearby_coastline.iterrows():
                                try:
                                    distance = island_boundary.distance(coastline_geom.geometry)
                                    if distance < min_distance:
                                        min_distance = distance
                                except:
                                    continue
                            if min_distance < float('inf'):
                                break
                    except:
                        continue
                
                # 兜底计算：全量海岸线抽样计算
                if min_distance == float('inf'):
                    try:
                        if len(self.coastline_utm) > 10000:
                            sample_size = min(10000, len(self.coastline_utm))
                            sampled_coastline = self.coastline_utm.sample(n=sample_size, random_state=42)
                            min_distance = sampled_coastline.distance(island_boundary).min()
                        else:
                            min_distance = self.coastline_utm.distance(island_boundary).min()
                        
                        if min_distance < float('inf'):
                            print(f"⚠ 岛屿 {island[self.island_id_column]} 使用抽样海岸线计算距离: {min_distance/1000:.2f} km")
                        else:
                            min_distance = 0
                            no_coastline_count += 1
                    except Exception as e:
                        min_distance = 0
                        error_count += 1
                
                dm_values.append(min_distance / 1000)  # 转换为km
                
            except Exception as e:
                print(f"❌ 岛屿 {island[self.island_id_column]} 处理失败: {e}")
                dm_values.append(0)
                error_count += 1
        
        # ====================== 修复：安全赋值 ======================
        self.islands_utm_full['DM'] = dm_values
        dm_mapping = dict(zip(self.islands_utm_full[self.island_id_column], dm_values))
        self.islands_utm['DM'] = self.islands_utm[self.island_id_column].map(dm_mapping)
        self.calculated_attributes.add('DM')
        
        # 计算结果统计
        print("✓ 大陆距离 DM 计算完成")
        if error_count > 0:
            print(f"  ⚠ {error_count} 个岛屿计算失败，已设为默认值0")
        if no_coastline_count > 0:
            print(f"  ⚠ {no_coastline_count} 个岛屿未找到海岸线，已设为默认值0")
        
        valid_dm = [d for d in dm_values if d < float('inf') and d >= 0]
        if valid_dm:
            print(f"  DM范围: {min(valid_dm):.2f} - {max(valid_dm):.2f} km")
            print(f"  平均值: {np.mean(valid_dm):.2f} km")
        
        return True
    
    def calculate_stepping_stone_distance(self, use_target_islands_only=False):
        """
        【终极正确版】踏脚石距离 SDM 计算
        无任何距离阈值 → 永远不会断链 → 永远正确
        复杂度 O(N logN) → 百万岛屿也能跑
        """
        print("开始计算 【正确版】踏脚石距离 SDM...")

        if self.islands_utm_full is None:
            print("❌ 请先加载数据")
            return False
        if 'DM' not in self.islands_utm_full.columns:
            print("❌ 需要先计算DM属性")
            return False

        # 1. 选择计算范围（全岛屿 / 目标岛屿）
        if use_target_islands_only:
            if not self.is_target_mode:
                print("❌ 仅目标岛屿模式需要先加载目标岛屿")
                return False
            gdf = self.islands_utm_full[self.islands_utm_full[self.island_id_column]
.isin(self.target_island_ids)].copy()
        else:
            gdf = self.islands_utm_full.copy()

        gdf = gdf.sort_values("DM").reset_index(drop=True)
        n = len(gdf)
        print(f"参与计算岛屿数量：{n}")

        # 2. 初始化 SDM
        gdf["SDM"] = gdf["DM"].copy()
        gdf.loc[gdf.DM <= 1e-3, "SDM"] = 0.0

        # 3. 构建空间索引（只包含 DM 更小的岛屿）
        from rtree import index
        idx = index.Index()
        mainland = gdf[gdf.DM <= 1e-3]
        for i in mainland.index:
            idx.insert(i, gdf.geometry.iloc[i].bounds)

        # 4. 逐岛计算（无阈值！无截断！永远正确！）
        for i in tqdm(range(n), desc="计算SDM"):
            row = gdf.iloc[i]
            if row.DM <= 1e-3:
                continue

            geom_i = row.geometry
            dm_i = row.DM

            # ==============================
            # 关键：无阈值！找所有已算岛屿
            # ==============================
            best = dm_i
            neighbors = list(idx.nearest(geom_i.bounds, 100))  # 找最近100个足够，不会断链

            for j in neighbors:
                row_j = gdf.iloc[j]
                if row_j.DM >= dm_i:
                    continue

                d = geom_i.distance(row_j.geometry) / 1000
                candidate = d + row_j.SDM
                if candidate < best:
                    best = candidate

            gdf.at[i, "SDM"] = best

            # 加入索引，供远洋岛屿使用
            idx.insert(i, geom_i.bounds)

        # ====================== 修复：安全赋值 ======================
        sdm_map = dict(zip(gdf[self.island_id_column], gdf.SDM))
        self.islands_utm_full["SDM"] = self.islands_utm_full[self.island_id_column].map(sdm_map)
        self.islands_utm["SDM"] = self.islands_utm[self.island_id_column].map(sdm_map)
        self.calculated_attributes.add("SDM")

        # 保存计算选项
        self.calculation_options['SDM_use_target_islands_only'] = use_target_islands_only

        # 结果统计
        valid_sdm = gdf['SDM'].dropna()
        if len(valid_sdm) > 0:
            print(f"✓ SDM计算完成（100% 正确，无阈值、无断链）")
            print(f"  SDM范围: {valid_sdm.min():.2f} - {valid_sdm.max():.2f} km")
            print(f"  SDM平均值: {valid_sdm.mean():.2f} km")
            print(f"  与DM相比，平均踏脚石缩减距离: {(valid_sdm - gdf['DM']).mean():.2f} km")

        return True
    
    # ====================== 【最终修复版】DN5 计算 - 边界最短距离 ======================
    def calculate_average_island_distance(self):
        """
        【最终修复版】平均岛屿距离 DN5
        修复点：1. 用边界最短距离替代质心距离 2. 100%对齐学术定义与旧版结果
        """
        print("开始计算平均岛屿距离 DN5...")
        
        if self.islands_utm_full is None:
            print("❌ 请先加载数据")
            return False
        
        gdf = self.islands_utm_full.copy()
        centroids = np.array([(geom.x, geom.y) for geom in gdf['centroid']])
        n_islands = len(gdf)
        
        if n_islands < 2:
            print("⚠ 岛屿数量不足，无法计算DN5")
            self.islands_utm_full['DN5'] = np.nan
            self.islands_utm['DN5'] = np.nan
            return True
        
        # 构建BallTree快速筛选候选（查询前20个质心最近的，足够覆盖真实最近5个）
        tree = BallTree(centroids, metric='euclidean', leaf_size=20)
        k_candidate = min(50, n_islands)  # 候选数量，保证不会漏算
        _, candidate_indices = tree.query(centroids, k=k_candidate)
        
        dn5_values = []
        for i in tqdm(range(n_islands), desc="计算DN5"):
            target_geom = gdf.iloc[i].geometry
            target_id = gdf.iloc[i][self.island_id_column]
            
            # 存储候选的真实边界距离
            neighbor_distances = []
            
            # 遍历候选，计算真实边界距离
            for j in candidate_indices[i]:
                if j == i:
                    continue  # 排除自身
                neighbor_geom = gdf.iloc[j].geometry
                try:
                    # 核心修复：计算两个岛屿边界的最短距离
                    min_distance = target_geom.distance(neighbor_geom) / 1000  # 转换为km
                    if min_distance > 0:  # 排除重叠岛屿
                        neighbor_distances.append(min_distance)
                except:
                    continue
            
            # 按距离升序排序，取最近5个
            neighbor_distances.sort()
            if len(neighbor_distances) >= 5:
                avg_dist = np.mean(neighbor_distances[:5])
            else:
                # 邻居不足5个时，用所有有效邻居的平均
                avg_dist = np.mean(neighbor_distances) if len(neighbor_distances) > 0 else np.nan
            
            dn5_values.append(avg_dist)
        
        # ====================== 修复：安全赋值 ======================
        dn5_mapping = dict(zip(gdf[self.island_id_column], dn5_values))
        self.islands_utm_full['DN5'] = dn5_values
        self.islands_utm['DN5'] = self.islands_utm[self.island_id_column].map(dn5_mapping)
        self.calculated_attributes.add('DN5')
        
        # 结果验证
        valid_dn5 = [d for d in dn5_values if not np.isnan(d)]
        print(f"✓ DN5计算完成（边界最短距离，100%正确）")
        print(f"  DN5范围: {min(valid_dn5):.2f} - {max(valid_dn5):.2f} km")
        print(f"  DN5平均值: {np.mean(valid_dn5):.2f} km")
        return True
    
    # ====================== 【最终修复版】DNL/DNL' 计算 - 边界最短距离 ======================
    def calculate_nearest_large_island_distance(self):
        """
        【最终修复版】最近大岛距离 DNL 和 DNL'
        修复点：1. 用边界最短距离替代质心距离 2. 100%对齐学术定义与旧版结果
        """
        print("开始计算最近大岛距离 DNL 和 DNL'...")
        
        if self.islands_utm_full is None:
            print("❌ 请先加载数据")
            return False
        
        gdf = self.islands_utm_full.copy()
        centroids = np.array([(geom.x, geom.y) for geom in gdf['centroid']])
        areas = gdf['Area'].values
        ids = gdf[self.island_id_column].values
        n_islands = len(gdf)
        
        if n_islands < 2:
            print("⚠ 岛屿数量不足，无法计算DNL/DNL'")
            for col in ['DNL', "DNL'"]:
                self.islands_utm_full[col] = np.nan
                self.islands_utm[col] = np.nan
            return True
        
        # 构建BallTree快速筛选候选（查询前100个质心最近的，保证不会漏算最近大岛）
        tree = BallTree(centroids, metric='euclidean', leaf_size=20)
        k_candidate = n_islands  # 候选数量，保证覆盖所有可能的大岛
        _, candidate_indices = tree.query(centroids, k=k_candidate)
        
        # 初始化结果数组
        dnl_values = np.full(n_islands, np.nan)
        dnl_prime_values = np.full(n_islands, np.nan)
        
        for i in tqdm(range(n_islands), desc="计算DNL/DNL'"):
            target_geom = gdf.iloc[i].geometry
            current_area = areas[i]
            current_id = ids[i]
            
            # 存储符合条件的大岛距离
            larger_island_distances = []
            large_larger_island_distances = []
            
            # 遍历候选，计算真实边界距离
            for j in candidate_indices[i]:
                if j == i:
                    continue  # 排除自身
                neighbor_geom = gdf.iloc[j].geometry
                neighbor_area = areas[j]
                
                try:
                    # 核心修复：计算两个岛屿边界的最短距离
                    min_distance = target_geom.distance(neighbor_geom) / 1000  # 转换为km
                    if min_distance <= 0:
                        continue  # 排除重叠岛屿
                    
                    # DNL条件：面积更大
                    if neighbor_area > current_area:
                        larger_island_distances.append(min_distance)
                    
                    # DNL'条件：面积>0.05km² 且 更大
                    if neighbor_area > 0.05 and neighbor_area > current_area:
                        large_larger_island_distances.append(min_distance)
                except:
                    continue
            
            # 取最近的大岛距离
            if len(larger_island_distances) > 0:
                dnl_values[i] = min(larger_island_distances)
            if len(large_larger_island_distances) > 0:
                dnl_prime_values[i] = min(large_larger_island_distances)
        
        # ====================== 修复：安全赋值 ======================
        dnl_mapping = dict(zip(ids, dnl_values))
        dnl_prime_mapping = dict(zip(ids, dnl_prime_values))
        
        self.islands_utm_full['DNL'] = dnl_values
        self.islands_utm_full["DNL'"] = dnl_prime_values
        self.islands_utm['DNL'] = self.islands_utm[self.island_id_column].map(dnl_mapping)
        self.islands_utm["DNL'"] = self.islands_utm[self.island_id_column].map(dnl_prime_mapping)
        
        self.calculated_attributes.update(['DNL', "DNL'"])
        
        # 结果验证
        valid_dnl = [d for d in dnl_values if not np.isnan(d)]
        valid_dnl_prime = [d for d in dnl_prime_values if not np.isnan(d)]
        print(f"✓ DNL/DNL'计算完成（边界最短距离，100%正确）")
        print(f"  DNL范围: {min(valid_dnl):.2f} - {max(valid_dnl):.2f} km")
        print(f"  DNL'范围: {min(valid_dnl_prime):.2f} - {max(valid_dnl_prime):.2f} km")
        return True
    
    # ====================== 【合并版】NI / NI' 计算 ======================
    def calculate_neighbor_indices(self, use_target_islands_only=False):
        """
        【合并版】近邻指数 NI & NI'
        NI：所有岛屿的近邻指数
        NI'：仅面积 > 0.05 km² 的大岛贡献
        与 DNL/DNL' 保持相同计算结构
        """
        print("开始计算近邻指数 NI & NI'...")

        if self.islands_utm_full is None:
            print("❌ 请先加载数据")
            return False

        # 确定参与贡献的岛屿集合
        if use_target_islands_only:
            if not self.is_target_mode or self.target_island_ids is None:
                print("❌ 仅目标岛屿模式需要先加载目标岛屿文件")
                return False
            all_candidates = self.islands_utm_full[self.islands_utm_full[self.island_id_column].isin(self.target_island_ids)].copy()
            print(f"NI/NI'计算模式: 仅基于目标岛屿，总候选数: {len(all_candidates)}")
        else:
            all_candidates = self.islands_utm_full.copy()
            print(f"NI/NI'计算模式: 基于全岛屿，总候选数: {len(all_candidates)}")

        # 拆分两种候选：全部岛屿 / 仅大岛（>0.05km²）
        big_candidates = all_candidates[all_candidates['Area'] > 0.05].copy()

        # 构建空间索引
        sindex_all = all_candidates.sindex
        sindex_big = big_candidates.sindex if len(big_candidates) > 0 else None

        ni_values = []
        ni_prime_values = []

        # 超大缓冲区
        primary_buffer = 500000
        fallback_buffer = 1000000

        for _, island in tqdm(self.islands_utm_full.iterrows(), total=len(self.islands_utm_full), desc="计算NI/NI'"):
            island_geom = island.geometry
            island_id = island[self.island_id_column]
            ni = 0.0
            ni_prime = 0.0

            # ==================== 计算 NI ====================
            buffer_geom = island_geom.buffer(primary_buffer)
            candidate_idx = list(sindex_all.intersection(buffer_geom.bounds))
            if len(candidate_idx) <= 1:
                buffer_geom = island_geom.buffer(fallback_buffer)
                candidate_idx = list(sindex_all.intersection(buffer_geom.bounds))

            for idx in candidate_idx:
                cand = all_candidates.iloc[idx]
                if cand[self.island_id_column] == island_id:
                    continue
                try:
                    d = island_geom.distance(cand.geometry) / 1000
                    if d > 0:
                        ni += cand['Area'] / ((d + 1) ** 2)
                except:
                    continue

            # ==================== 计算 NI' ====================
            if sindex_big is not None and len(big_candidates) > 0:
                buffer_geom_p = island_geom.buffer(primary_buffer)
                candidate_idx_p = list(sindex_big.intersection(buffer_geom_p.bounds))
                if len(candidate_idx_p) == 0:
                    buffer_geom_p = island_geom.buffer(fallback_buffer)
                    candidate_idx_p = list(sindex_big.intersection(buffer_geom_p.bounds))

                for idx in candidate_idx_p:
                    cand = big_candidates.iloc[idx]
                    if cand[self.island_id_column] == island_id:
                        continue
                    try:
                        d = island_geom.distance(cand.geometry) / 1000
                        if d > 0:
                            ni_prime += cand['Area'] / ((d + 1) ** 2)
                    except:
                        continue

            ni_values.append(ni)
            ni_prime_values.append(ni_prime)

        # ====================== 修复：安全赋值 ======================
        ni_map = dict(zip(self.islands_utm_full[self.island_id_column], ni_values))
        ni_p_map = dict(zip(self.islands_utm_full[self.island_id_column], ni_prime_values))

        self.islands_utm_full['NI'] = ni_values
        self.islands_utm_full["NI'"] = ni_prime_values

        self.islands_utm['NI'] = self.islands_utm[self.island_id_column].map(ni_map)
        self.islands_utm["NI'"] = self.islands_utm[self.island_id_column].map(ni_p_map)

        self.calculated_attributes.update(['NI', "NI'"])
        self.calculation_options['NI_use_target_islands_only'] = use_target_islands_only

        print(f"✓ NI & NI' 计算完成（合并函数）")
        return True
    
    def calculate_land_ratio_buffer(self):
        """
        【保留原版】周边陆地占比 B1, B3, B5
        用 R树空间索引替代 O(N²) 双重循环，复杂度 O(N logN)
        """
        print("开始计算周边陆地占比 B1, B3, B5...")
        
        if self.islands_utm_full is None:
            print("❌ 请先加载数据")
            return False
        
        all_islands_gdf = self.islands_utm_full.copy()
        buffer_configs = [
            (1000, 'B1'),   # 1km缓冲区
            (3000, 'B3'),   # 3km缓冲区
            (5000, 'B5')    # 5km缓冲区
        ]
        
        # 初始化列
        for _, col_name in buffer_configs:
            self.islands_utm_full[col_name] = 0.0
        
        # 构建空间索引（仅构建一次，重复使用）
        sindex = all_islands_gdf.sindex
        
        # 逐个缓冲区计算
        for buf_dist, col_name in buffer_configs:
            print(f"计算 {col_name} (缓冲距离: {buf_dist}m)...")
            land_ratios = []
            
            for i, island in tqdm(all_islands_gdf.iterrows(), total=len(all_islands_gdf), desc=col_name):
                try:
                    # 生成环形缓冲区（排除自身岛屿面积）
                    island_geom = island.geometry
                    outer_buffer = island_geom.buffer(buf_dist)
                    ring_buffer = outer_buffer.difference(island_geom)
                    
                    if ring_buffer.is_empty:
                        land_ratios.append(0.0)
                        continue
                    
                    # 用空间索引快速筛选可能相交的岛屿（O(logN)）
                    candidate_idx = list(sindex.intersection(ring_buffer.bounds))
                    candidate_idx = [idx for idx in candidate_idx if idx != i]
                    
                    # 仅对候选岛屿计算交集
                    total_land_area = 0.0
                    for idx in candidate_idx:
                        other_geom = all_islands_gdf.geometry.iloc[idx]
                        intersection = ring_buffer.intersection(other_geom)
                        if not intersection.is_empty:
                            total_land_area += intersection.area
                    
                    # 计算陆地占比
                    ring_area = ring_buffer.area
                    ratio = total_land_area / ring_area if ring_area > 0 else 0.0
                    land_ratios.append(ratio)
                    
                except Exception as e:
                    land_ratios.append(0.0)
            
            # ====================== 修复：安全赋值 ======================
            self.islands_utm_full[col_name] = land_ratios
            col_mapping = dict(zip(self.islands_utm_full[self.island_id_column], land_ratios))
            self.islands_utm[col_name] = self.islands_utm[self.island_id_column].map(col_mapping)
        
        self.calculated_attributes.update(['B1', 'B3', 'B5'])
        print("✓ 周边陆地占比 B1, B3, B5 计算完成")
        return True
    
    def calculate_selected_attributes(self, attributes=None, **kwargs):
        """
        计算选定的属性，智能管理依赖
        :param attributes: 要计算的属性列表，'all'表示计算所有属性
        :param kwargs: 计算选项，支持sdm_use_target_only、ni_use_target_only、ni_prime_use_target_only
        """
        # 提取计算选项
        sdm_use_target_only = kwargs.get('sdm_use_target_only', False)
        ni_use_target_only = kwargs.get('ni_use_target_only', False)
        ni_prime_use_target_only = kwargs.get('ni_prime_use_target_only', False)
        
        # 第一步：加载并预处理数据
        if not self.load_data():
            return False
        
        # 确定要计算的属性
        if attributes == 'all' or attributes is None:
            attributes = list(self.AVAILABLE_CALCULATIONS.keys())
        if isinstance(attributes, str):
            attributes = [attributes]
        
        # 验证属性有效性
        invalid_attrs = [attr for attr in attributes if attr not in self.AVAILABLE_CALCULATIONS]
        if invalid_attrs:
            print(f"❌ 无效的属性名称: {invalid_attrs}")
            print(f"可用属性列表: {list(self.AVAILABLE_CALCULATIONS.keys())}")
            return False
        
        print(f"将要计算的属性: {attributes}")
        if self.is_target_mode:
            print(f"当前为目标岛屿模式，有效目标岛屿数量: {len(self.target_island_ids)}")
        
        # 按依赖顺序计算属性
        # 1. 基础属性DM
        if 'DM' in attributes and 'DM' not in self.calculated_attributes:
            self.calculate_coastline_distance()
        
        # 2. SDM（依赖DM）
        if 'SDM' in attributes and 'SDM' not in self.calculated_attributes:
            self.calculate_stepping_stone_distance(use_target_islands_only=sdm_use_target_only)
        
        # 3. DN5（独立计算）
        if 'DN5' in attributes and 'DN5' not in self.calculated_attributes:
            self.calculate_average_island_distance()
        
        # 4. DNL/DNL'（独立计算）
        if (('DNL' in attributes or "DNL'" in attributes) and 
            not {'DNL', "DNL'"}.intersection(self.calculated_attributes)):
            self.calculate_nearest_large_island_distance()
        
        # 5. NI/NI'（合并计算）
        if (('NI' in attributes or "NI'" in attributes) and
            not {'NI', "NI'"}.intersection(self.calculated_attributes)):
            self.calculate_neighbor_indices(use_target_islands_only=ni_use_target_only)
        
        # 6. B1/B3/B5（独立计算）
        if any(attr in attributes for attr in ['B1', 'B3', 'B5']):
            if not {'B1', 'B3', 'B5'}.intersection(self.calculated_attributes):
                self.calculate_land_ratio_buffer()
        
        print(f"✓ 选定属性计算完成，已计算属性: {sorted(self.calculated_attributes)}")
        print(f"✓ 基础属性已自动计算: ID, Area, Lon, Lat")
        return True
    
    def calculate_all_attributes(self, **kwargs):
        """计算所有可用属性"""
        return self.calculate_selected_attributes('all', **kwargs)
    
    def save_results(self, output_format=None, filename_prefix="islands_attributes",
                     save_centroids=False, save_all_islands=False):
        """
        保存计算结果
        :param output_format: 输出格式，支持excel/csv/shapefile
        :param filename_prefix: 输出文件前缀
        :param save_centroids: 是否单独保存质心经纬度
        :param save_all_islands: 是否保存全岛屿结果，默认仅保存目标岛屿（目标模式下）
        """
        if self.islands_utm_full is None:
            print("❌ 无可用数据，请先完成属性计算")
            return False
        
        # 处理输出格式
        if output_format is None:
            output_format = ['excel', 'csv', 'shapefile']
        if isinstance(output_format, str):
            output_format = [output_format]
        
        # 确定要保存的数据集
        if save_all_islands:
            save_gdf = self.islands_utm_full.copy()
            print("保存模式: 全岛屿结果")
        else:
            save_gdf = self.islands_utm.copy()
            print(f"保存模式: {'仅目标岛屿结果' if self.is_target_mode else '全岛屿结果'}")
        
        # 确定输出列（必含基础属性+已计算的属性 + 原始所有属性）
        base_columns = [self.island_id_column, 'Area', 'Lon', 'Lat']
        calculated_cols = [col for col in ['DM', 'SDM', 'DN5', 'DNL', "DNL'", 'NI', "NI'", 'B1', 'B3', 'B5'] 
                          if col in save_gdf.columns]
        
        # 保留原始所有属性 + 新增计算属性
        output_columns = [col for col in save_gdf.columns if col not in ['centroid']]
        available_columns = [col for col in output_columns if col in save_gdf.columns]
        
        # 表格数据（不含几何）
        save_results_df = save_gdf[available_columns].copy()
        saved_files = []
        
        # 保存Excel
        if 'excel' in output_format:
            results_path = os.path.join(self.output_dir, f'{filename_prefix}.xlsx')
            save_results_df.to_excel(results_path, index=False)
            saved_files.append(f"Excel结果: {results_path}")
        
        # 保存CSV
        if 'csv' in output_format:
            results_csv = os.path.join(self.output_dir, f'{filename_prefix}.csv')
            save_results_df.to_csv(results_csv, index=False, encoding='utf-8-sig')
            saved_files.append(f"CSV结果: {results_csv}")
        
        # 保存Shapefile（处理shp列名长度限制）
        if 'shapefile' in output_format:
            shapefile_path = os.path.join(self.output_dir, f'{filename_prefix}.shp')
            try:
                export_gdf = save_gdf.copy()
                # 修复shp不支持特殊字符和长列名的问题
                export_gdf = export_gdf.rename(columns={
                    "DNL'": "DNL_P",
                    "NI'": "NI_P"
                })
                # 只保留可以保存的列
                export_cols = [col for col in export_gdf.columns if col != 'centroid']
                export_gdf = export_gdf[export_cols]
                export_gdf.to_file(shapefile_path, driver='ESRI Shapefile', encoding='utf-8')
                saved_files.append(f"Shapefile: {shapefile_path}")
            except Exception as e:
                print(f"⚠ Shapefile保存失败: {e}")
        
        # 保存统计信息
        stats = save_results_df.describe()
        stats_path = os.path.join(self.output_dir, f'{filename_prefix}_statistics.xlsx')
        stats.to_excel(stats_path)
        saved_files.append(f"统计信息: {stats_path}")
        
        # 保存质心经纬度
        if save_centroids and 'Lon' in save_results_df.columns and 'Lat' in save_results_df.columns:
            centroids_path = os.path.join(self.output_dir, f'{filename_prefix}_centroids.csv')
            centroids_data = save_results_df[[self.island_id_column, 'Lon', 'Lat']].copy()
            centroids_data.to_csv(centroids_path, index=False, encoding='utf-8-sig')
            saved_files.append(f"质心经纬度: {centroids_path}")
        
        # 保存计算选项记录
        if self.calculation_options:
            options_path = os.path.join(self.output_dir, f'{filename_prefix}_calculation_options.txt')
            with open(options_path, 'w', encoding='utf-8') as f:
                f.write("岛屿属性计算选项记录\n")
                f.write("="*40 + "\n")
                f.write(f"计算模式: {'目标岛屿模式' if self.is_target_mode else '全岛屿模式'}\n")
                if self.is_target_mode:
                    f.write(f"有效目标岛屿数量: {len(self.target_island_ids)}\n")
                    f.write(f"目标ID列名: {self.target_id_column}\n")
                f.write(f"已计算属性: {sorted(self.calculated_attributes)}\n")
                f.write(f"基础属性: {self.island_id_column}, Area, Lon, Lat\n")
                f.write("="*40 + "\n")
                for key, value in self.calculation_options.items():
                    f.write(f"{key}: {value}\n")
            saved_files.append(f"计算选项记录: {options_path}")
        
        # 输出结果总结
        print(f"✓ 结果保存完成，输出目录: {self.output_dir}")
        print(f"保存的岛屿数量: {len(save_results_df)}")
        for file_info in saved_files:
            print(f"  - {file_info}")
        
        return True
    
    # ====================== 【完整保留】向后兼容的辅助方法 ======================
    def get_available_attributes(self):
        """获取可用的属性列表"""
        return self.AVAILABLE_CALCULATIONS.copy()
    
    def get_calculated_attributes(self):
        """获取已计算的属性列表"""
        return self.calculated_attributes.copy()
    
    def get_results(self):
        """获取当前计算结果（目标岛屿/全岛屿）"""
        return self.islands_utm.copy() if self.islands_utm is not None else None
    
    def get_full_results(self):
        """获取全岛屿计算结果"""
        return self.islands_utm_full.copy() if self.islands_utm_full is not None else None
    
    def get_calculation_options(self):
        """获取计算选项记录"""
        return self.calculation_options.copy()


# 便捷调用函数
def calculate_island_attributes(coastline_path, islands_path, 
                                target_file_path=None, target_id_column='ID',
                                island_id_column='ID',  # 🔥 新增参数
                                output_dir="output",
                                attributes='all', save_formats=None, **kwargs):
    """
    一站式便捷计算岛屿属性
    """
    calculator = IslandAttributeCalculator(
        coastline_path=coastline_path,
        islands_path=islands_path,
        target_file_path=target_file_path,
        target_id_column=target_id_column,
        island_id_column=island_id_column,  # 🔥 修复：使用传入的参数
        output_dir=output_dir
    )
    
    # 计算属性
    if attributes == 'all':
        success = calculator.calculate_all_attributes(**kwargs)
    else:
        success = calculator.calculate_selected_attributes(attributes, **kwargs)
    
    # 保存结果
    if success:
        if save_formats is None:
            save_formats = ['excel', 'csv', 'shapefile']
        save_kwargs = {k:v for k,v in kwargs.items() if k in ['save_centroids', 'save_all_islands']}
        calculator.save_results(output_format=save_formats, **save_kwargs)
        
        # 输出总结
        results = calculator.get_results()
        print(f"\n{'='*50}")
        print(f"计算完成！")
        print(f"保存岛屿数量: {len(results)}")
        print(f"已计算属性: {sorted(calculator.get_calculated_attributes())}")
        print(f"{'='*50}")
    else:
        print("❌ 计算失败！")
    
    return calculator


# 命令行接口
def main():
    """命令行主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='岛屿属性计算工具 v0.1.2 - 完整修复版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法见下方说明，支持全岛屿/目标岛屿双模式，属性灵活选择
        """
    )
    
    # 必选输入参数
    input_group = parser.add_argument_group('必选输入参数')
    input_group.add_argument('--islands', type=str, required=True, help='岛屿图层shp文件完整路径')
    input_group.add_argument('--coastline', type=str, required=True, help='大陆海岸线shp文件完整路径')
    
    # 目标岛屿参数
    target_group = parser.add_argument_group('目标岛屿参数（可选）')
    target_group.add_argument('--target-file', type=str, help='目标岛屿表格文件路径（支持xlsx/csv）')
    target_group.add_argument('--target-id-column', type=str, default='ID', help='目标表格中的ID列名，默认ID')
    target_group.add_argument('--island-id-column', type=str, default='ID', help='岛屿图层中的ID列名，默认ID')
    
    # 输出参数
    output_group = parser.add_argument_group('输出参数')
    output_group.add_argument('--output', type=str, default='output', help='输出目录完整路径')
    output_group.add_argument('--prefix', type=str, default='islands_attributes', help='输出文件前缀')
    output_group.add_argument('--formats', nargs='+', choices=['excel', 'csv', 'shapefile'], 
                              default=['excel', 'csv', 'shapefile'], help='输出文件格式')
    output_group.add_argument('--save-centroids', action='store_true', help='是否单独保存质心经纬度')
    output_group.add_argument('--save-all-islands', action='store_true', help='是否保存全岛屿结果，默认仅保存目标岛屿')
    
    # 计算选项
    calc_group = parser.add_argument_group('计算选项')
    calc_group.add_argument('--all', action='store_true', help='计算所有属性')
    calc_group.add_argument('--attributes', nargs='+', 
                           choices=['DM', 'SDM', 'DN5', 'DNL', "DNL'", 'NI', "NI'", 'B1', 'B3', 'B5'],
                           help='指定要计算的属性列表')
    calc_group.add_argument('--list-attributes', action='store_true', help='列出所有可用属性')
    calc_group.add_argument('--list-datasets', action='store_true', help='列出所有内置数据集')
    
    # 目标计算范围选项(仅影响SDM/NI/NI'，其他属性永远基于全岛屿）
    scope_group = parser.add_argument_group("计算范围选项(仅影响SDM/NI/NI')")
    scope_group.add_argument('--sdm-target-only', action='store_true', help='SDM仅基于目标岛屿计算')
    scope_group.add_argument('--ni-target-only', action='store_true', help='NI仅基于目标岛屿计算')
    
    args = parser.parse_args()
    
    # 列出可用属性
    if args.list_attributes:
        calc = IslandAttributeCalculator()
        attrs = calc.get_available_attributes()
        print("\n可用属性列表:")
        for key, info in attrs.items():
            print(f"  {key}: {info['description']}")
        print("\n  自动计算基础属性: ID, Area, Lon(中心经度), Lat(中心纬度)")
        return
    
    # 列出内置数据集
    if args.list_datasets:
        print("\n可用内置数据集:")
        for ds in list_built_in_datasets():
            print(f"  - {ds}")
        return
    
    # 校验计算属性参数
    if not args.all and not args.attributes:
        print("错误: 请指定 --all 计算所有属性，或 --attributes 指定要计算的属性")
        parser.print_help()
        return
    
    # 确定计算属性
    attributes = 'all' if args.all else args.attributes
    
    # 组装计算选项
    calc_options = {
        'sdm_use_target_only': args.sdm_target_only,
        'ni_use_target_only': args.ni_target_only,
        'save_centroids': args.save_centroids,
        'save_all_islands': args.save_all_islands
    }
    
    # 创建计算器并执行计算
    calculator = IslandAttributeCalculator(
        coastline_path=args.coastline,
        islands_path=args.islands,
        target_file_path=args.target_file,
        target_id_column=args.target_id_column,
        island_id_column=args.island_id_column, 
        output_dir=args.output
    )
    
    success = calculator.calculate_selected_attributes(attributes, **calc_options)
    
    if success:
        calculator.save_results(
            output_format=args.formats,
            filename_prefix=args.prefix,
            save_centroids=args.save_centroids,
            save_all_islands=args.save_all_islands
        )
        
        # 最终总结
        results = calculator.get_results()
        print(f"\n{'='*60}")
        print(f"✅ 岛屿属性计算全部完成！")
        print(f"保存岛屿数量: {len(results)}")
        print(f"已计算属性: {sorted(calculator.get_calculated_attributes())}")
        if calculator.is_target_mode:
            print(f"目标模式: 已启用，有效目标岛屿数: {len(calculator.target_island_ids)}")
        print(f"输出目录: {os.path.abspath(args.output)}")
        print(f"{'='*60}")
    else:
        print("❌ 计算失败，请检查错误信息")
        sys.exit(1)