import requests
import json
from datetime import datetime, timedelta
import time
import os
from typing import Dict, List, Optional
import pandas as pd
import matplotlib.pyplot as plt


class CmcFearGreedAPI:
    def __init__(self, api_key: str = None):
        """
        初始化CoinMarketCap恐惧贪婪指数API

        Args:
            api_key: CoinMarketCap API密钥，如果为None则从环境变量读取
        """
        self.base_url = "https://pro-api.coinmarketcap.com/v3/fear-and-greed"
        self.api_key = api_key or os.getenv('COINMARKETCAP_API_KEY','X-CMC_PRO_API_KEY: ')
        
        if not self.api_key:
            raise ValueError("请提供CoinMarketCap API密钥或设置COINMARKETCAP_API_KEY环境变量")
        
        self.headers = {
            'X-CMC_PRO_API_KEY': self.api_key,
            'Accept': 'application/json',
            'User-Agent': 'FearGreedIndexBot/1.0'
        }
    
    def get_current_index(self) -> Optional[Dict]:
        """
        获取当前恐惧贪婪指数

        Returns:
            dict: 包含指数数据的字典，如果失败返回None
        """
        try:
            url = f"{self.base_url}/latest"
            
            print("🔍 正在获取当前恐惧贪婪指数...")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查API响应状态
            if data.get('status', {}).get('error_code') != 0:
                error_msg = data.get('status', {}).get('error_message', 'Unknown error')
                print(f"❌ API返回错误: {error_msg}")
                return None
            
            index_data = data.get('data', {})
            
            # 格式化返回数据
            result = {
                'value': index_data.get('value'),
                'classification': index_data.get('value_classification'),
                'update_time': index_data.get('update_time'),
                'timestamp': datetime.now().isoformat(),
                'source': 'CoinMarketCap Official API'
            }
            
            return result
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求错误: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 发生未知错误: {e}")
            return None
    
    def get_historical_data(self, start: int = 1, limit: int = 50) -> Optional[List[Dict]]:
        """
        获取历史恐惧贪婪指数数据

        Args:
            start: 起始位置 (1-based index)
            limit: 返回结果数量 (1-500)

        Returns:
            list: 历史数据列表
        """
        try:
            url = f"{self.base_url}/historical"
            params = {
                'start': max(1, start),
                'limit': min(500, max(1, limit))
            }
            
            print(f"📊 正在获取历史恐惧贪婪指数数据 (start={start}, limit={limit})...")
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查API响应状态
            if data.get('status', {}).get('error_code') != 0:
                error_msg = data.get('status', {}).get('error_message', 'Unknown error')
                print(f"❌ API返回错误: {error_msg}")
                return None
            
            historical_data = data.get('data', [])
            
            # 处理时间戳并添加可读日期
            for item in historical_data:
                timestamp = int(item['timestamp'])
                item['date'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                item['datetime'] = datetime.fromtimestamp(timestamp)
            
            return historical_data
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求错误: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 获取历史数据失败: {e}")
            return None


class FearGreedAnalyzer:
    @staticmethod
    def interpret_index(value: int) -> Dict:
        """
        解读恐惧贪婪指数

        Args:
            value: 指数值 (0-100)

        Returns:
            dict: 包含解读信息的字典
        """
        if 0 <= value <= 25:
            return {
                'level': '极度恐惧',
                'emoji': '🔴',
                'sentiment': '极度悲观',
                'description': '市场情绪极度悲观，投资者普遍恐惧',
                'suggestion': '可能是不错的买入机会，但需谨慎',
                'color': 'red'
            }
        elif 26 <= value <= 46:
            return {
                'level': '恐惧',
                'emoji': '🟠',
                'sentiment': '悲观',
                'description': '市场情绪悲观，存在不确定性',
                'suggestion': '谨慎观望，可考虑小仓位建仓',
                'color': 'orange'
            }
        elif 47 <= value <= 54:
            return {
                'level': '中性',
                'emoji': '🟡',
                'sentiment': '平衡',
                'description': '市场情绪相对平衡',
                'suggestion': '正常交易区间，按计划执行策略',
                'color': 'yellow'
            }
        elif 55 <= value <= 75:
            return {
                'level': '贪婪',
                'emoji': '🟢',
                'sentiment': '乐观',
                'description': '市场情绪乐观，投资者信心较强',
                'suggestion': '注意风险管理，考虑部分获利了结',
                'color': 'green'
            }
        else:  # 76-100
            return {
                'level': '极度贪婪',
                'emoji': '🔴',
                'sentiment': '极度乐观',
                'description': '市场极度狂热，投资者过度自信',
                'suggestion': '高风险区域，建议减仓并设置止盈',
                'color': 'darkred'
            }
    
    @staticmethod
    def format_timestamp(timestamp_str: str) -> str:
        """
        格式化时间戳

        Args:
            timestamp_str: ISO格式的时间字符串

        Returns:
            str: 格式化后的时间字符串
        """
        try:
            # 移除时区信息以便解析
            clean_timestamp = timestamp_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return timestamp_str
    
    @staticmethod
    def analyze_historical_trend(historical_data: List[Dict]) -> Dict:
        """
        分析历史数据趋势

        Args:
            historical_data: 历史数据列表

        Returns:
            dict: 趋势分析结果
        """
        if not historical_data:
            return {}
        
        values = [item['value'] for item in historical_data]
        dates = [item['datetime'] for item in historical_data]
        
        # 基础统计
        avg_value = sum(values) / len(values)
        max_value = max(values)
        min_value = min(values)
        
        # 趋势分析
        recent_5 = values[:5]
        previous_5 = values[5:10]
        
        recent_avg = sum(recent_5) / len(recent_5)
        previous_avg = sum(previous_5) / len(previous_5) if len(previous_5) > 0 else recent_avg
        
        trend = "上升" if recent_avg > previous_avg else "下降"
        trend_strength = abs(recent_avg - previous_avg)
        
        # 情绪分布
        sentiment_counts = {
            '极度恐惧': len([v for v in values if v <= 25]),
            '恐惧': len([v for v in values if 26 <= v <= 46]),
            '中性': len([v for v in values if 47 <= v <= 54]),
            '贪婪': len([v for v in values if 55 <= v <= 75]),
            '极度贪婪': len([v for v in values if v >= 76])
        }
        
        dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        
        return {
            'period_days': len(historical_data),
            'average_value': round(avg_value, 2),
            'max_value': max_value,
            'min_value': min_value,
            'current_value': values[0],
            'trend': trend,
            'trend_strength': round(trend_strength, 2),
            'volatility': max_value - min_value,
            'sentiment_distribution': sentiment_counts,
            'dominant_sentiment': dominant_sentiment,
            'date_range': {
                'start': dates[-1].strftime('%Y-%m-%d'),
                'end': dates[0].strftime('%Y-%m-%d')
            }
        }


def display_current_index(data: Dict):
    """
    显示当前恐惧贪婪指数

    Args:
        data: 指数数据字典
    """
    if not data:
        print("❌ 没有有效数据可显示")
        return
    
    value = data['value']
    interpretation = FearGreedAnalyzer.interpret_index(value)
    formatted_time = FearGreedAnalyzer.format_timestamp(data['update_time'])
    
    print("\n" + "=" * 70)
    print("🎯 COINMARKETCAP 恐惧贪婪指数")
    print("=" * 70)
    print(f"{interpretation['emoji']} 当前指数: {value} - {interpretation['level']}")
    print(f"📊 官方分类: {data['classification']}")
    print(f"🕒 更新时间: {formatted_time}")
    print(f"🌐 数据来源: {data['source']}")
    print("=" * 70)
    
    # 显示进度条
    progress_bar = "[" + "█" * (value // 2) + " " * (50 - value // 2) + "]"
    print(f"📈 情绪刻度: {progress_bar}")
    print(f"  0 {'恐惧':<15} 50 {'中性':<15} 100")
    print("")
    
    # 显示详细解读
    print("📋 市场分析:")
    print(f"  💭 情绪状态: {interpretation['sentiment']}")
    print(f"  📝 描述: {interpretation['description']}")
    print(f"  💡 操作建议: {interpretation['suggestion']}")
    print("=" * 70)


def display_historical_data(historical_data: List[Dict], show_trend_analysis: bool = True):
    """
    显示历史恐惧贪婪指数数据

    Args:
        historical_data: 历史数据列表
        show_trend_analysis: 是否显示趋势分析
    """
    if not historical_data:
        print("❌ 没有历史数据可显示")
        return
    
    print(f"\n📅 恐惧贪婪指数历史数据 (共{len(historical_data)}条)")
    print("=" * 80)
    print(f"{'日期':<12} {'指数':<6} {'等级':<12} {'情绪':<8}")
    print("-" * 80)
    
    for i, item in enumerate(historical_data):
        value = item['value']
        interpretation = FearGreedAnalyzer.interpret_index(value)
        
        # 每10条数据显示一次日期，避免过于拥挤
        if i % 10 == 0 or i == len(historical_data) - 1:
            date_str = item['date']
        else:
            date_str = ""
        
        print(f"{date_str:<12} {value:<6} {item['value_classification']:<12} {interpretation['emoji']:<8}")
    
    print("=" * 80)
    
    # 显示趋势分析
    if show_trend_analysis:
        trend_analysis = FearGreedAnalyzer.analyze_historical_trend(historical_data)
        
        if trend_analysis:
            print("\n📈 历史趋势分析:")
            print(f"  📊 数据期间: {trend_analysis['date_range']['start']} 至 {trend_analysis['date_range']['end']}")
            print(f"  📍 当前指数: {trend_analysis['current_value']}")
            print(f"  📍 期间均值: {trend_analysis['average_value']}")
            print(f"  📍 波动范围: {trend_analysis['min_value']} - {trend_analysis['max_value']}")
            print(f"  📍 趋势方向: {trend_analysis['trend']}")
            print(f"  📍 趋势强度: {trend_analysis['trend_strength']}")
            print(f"  📍 主要情绪: {trend_analysis['dominant_sentiment']}")
            
            # 情绪分布
            print(f"  📊 情绪分布:")
            for sentiment, count in trend_analysis['sentiment_distribution'].items():
                if count > 0:
                    percentage = (count / len(historical_data)) * 100
                    print(f"     {sentiment}: {count}次 ({percentage:.1f}%)")


def plot_historical_data(historical_data: List[Dict]):
    """
    绘制历史数据图表

    Args:
        historical_data: 历史数据列表
    """
    if not historical_data:
        print("❌ 没有数据可绘制图表")
        return
    
    try:
        # 准备数据
        dates = [item['datetime'] for item in historical_data]
        values = [item['value'] for item in historical_data]
        classifications = [item['value_classification'] for item in historical_data]
        
        # 创建颜色映射
        color_map = {
            'Extreme Fear': 'red',
            'Fear': 'orange',
            'Neutral': 'yellow',
            'Greed': 'green',
            'Extreme Greed': 'darkred'
        }
        
        colors = [color_map.get(cls, 'gray') for cls in classifications]
        
        # 创建图表
        plt.figure(figsize=(12, 8))
        
        # 绘制折线图
        plt.plot(dates, values, marker='o', linewidth=2, markersize=4, color='blue', alpha=0.6)
        
        # 绘制散点图（按情绪着色）
        plt.scatter(dates, values, c=colors, s=50, alpha=0.7)
        
        # 添加区域标注
        plt.axhspan(0, 25, alpha=0.2, color='red', label='极度恐惧')
        plt.axhspan(26, 46, alpha=0.2, color='orange', label='恐惧')
        plt.axhspan(47, 54, alpha=0.2, color='yellow', label='中性')
        plt.axhspan(55, 75, alpha=0.2, color='green', label='贪婪')
        plt.axhspan(76, 100, alpha=0.2, color='darkred', label='极度贪婪')
        
        # 设置图表属性
        plt.title('加密货币恐惧贪婪指数历史走势', fontsize=16, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('恐惧贪婪指数', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 旋转日期标签
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 显示图表
        plt.show()
        
        # 保存图表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fear_greed_index_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"💾 图表已保存为: {filename}")
    
    except Exception as e:
        print(f"❌ 绘制图表时出错: {e}")


def export_to_csv(historical_data: List[Dict], filename: str = None):
    """
    导出历史数据到CSV文件

    Args:
        historical_data: 历史数据列表
        filename: 输出文件名
    """
    if not historical_data:
        print("❌ 没有数据可导出")
        return
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fear_greed_index_{timestamp}.csv"
    
    try:
        # 准备数据
        df_data = []
        for item in historical_data:
            df_data.append({
                'date': item['date'],
                'timestamp': item['timestamp'],
                'value': item['value'],
                'classification': item['value_classification'],
                'datetime': item['datetime']
            })
        
        df = pd.DataFrame(df_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"💾 数据已导出到: {filename}")
    
    except Exception as e:
        print(f"❌ 导出数据时出错: {e}")


def main_menu():
    """
    主菜单界面
    """
    API_KEY = ""  # 替换为你的实际API密钥
    
    try:
        cmc_api = CmcFearGreedAPI(api_key=API_KEY)
        
        while True:
            print("\n" + "=" * 60)
            print("🎯 COINMARKETCAP 恐惧贪婪指数分析工具")
            print("=" * 60)
            print("1. 📊 查看当前指数")
            print("2. 📅 查看历史数据")
            print("3. 📈 绘制历史图表")
            print("4. 💾 导出数据到CSV")
            print("5. 🔄 持续监控模式")
            print("0. ❌ 退出程序")
            print("=" * 60)
            
            choice = input("请选择操作 (0-5): ").strip()
            
            if choice == '1':
                # 查看当前指数
                data = cmc_api.get_current_index()
                display_current_index(data)
            
            elif choice == '2':
                # 查看历史数据
                try:
                    start = int(input("起始位置 (默认1): ") or 1)
                    limit = int(input("数据条数 (1-500, 默认50): ") or 50)
                except ValueError:
                    start, limit = 1, 50
                
                historical_data = cmc_api.get_historical_data(start=start, limit=limit)
                display_historical_data(historical_data)
            
            elif choice == '3':
                # 绘制历史图表
                historical_data = cmc_api.get_historical_data(limit=30)
                plot_historical_data(historical_data)
            
            elif choice == '4':
                # 导出数据到CSV
                historical_data = cmc_api.get_historical_data(limit=100)
                export_to_csv(historical_data)
            
            elif choice == '5':
                # 持续监控模式
                print("\n🔄 进入持续监控模式...")
                print("按 Ctrl+C 停止监控")
                
                try:
                    monitor_interval = 300  # 5分钟
                    while True:
                        data = cmc_api.get_current_index()
                        if data:
                            display_current_index(data)
                        
                        print(f"\n⏰ 下次更新在 {monitor_interval // 60} 分钟后...")
                        time.sleep(monitor_interval)
                
                except KeyboardInterrupt:
                    print("\n👋 退出监控模式")
            
            elif choice == '0':
                print("👋 感谢使用，再见！")
                break
            
            else:
                print("❌ 无效选择，请重新输入")
            
            if choice != '0':
                input("\n按 Enter 键继续...")
    
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序运行错误: {e}")


if __name__ == "__main__":
    # 安装依赖: pip install requests pandas matplotlib seaborn
    
    main_menu()