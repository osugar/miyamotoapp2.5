import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
from typing import Optional, Dict, Any
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataManager:
    """データ管理クラス"""
    
    def __init__(self, csv_path: str = 'sales_test_data_utf8.csv'):
        self.csv_path = csv_path
        self._df = None
    
    @st.cache_data
    def load_data(_self) -> pd.DataFrame:
        """データを読み込み、キャッシュする"""
        try:
            df = pd.read_csv(_self.csv_path)
            
            # データ検証
            required_columns = ['売上年月', '商品名', '担当者', '顧客名', '売上金額', '仕入れ金額', '粗利金額']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"必要な列が不足しています: {missing_columns}")
            
            # データ型変換
            df['売上年月'] = pd.to_datetime(df['売上年月'], format='%Y-%m', errors='coerce')
            
            # 数値列の検証
            numeric_columns = ['売上金額', '仕入れ金額', '粗利金額']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 欠損値の確認
            null_counts = df.isnull().sum()
            if null_counts.any():
                logger.warning(f"欠損値が検出されました: {null_counts[null_counts > 0]}")
            
            logger.info(f"データ読み込み完了: {len(df)}件")
            return df
            
        except FileNotFoundError:
            st.error(f"CSVファイルが見つかりません: {_self.csv_path}")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"データ読み込みエラー: {str(e)}")
            logger.error(f"データ読み込みエラー: {str(e)}")
            return pd.DataFrame()
    
    def validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """データの品質を検証する"""
        validation_result = {
            'is_valid': True,
            'issues': [],
            'summary': {}
        }
        
        try:
            # 基本統計
            validation_result['summary'] = {
                'total_records': len(df),
                'date_range': f"{df['売上年月'].min().strftime('%Y-%m')} 〜 {df['売上年月'].max().strftime('%Y-%m')}",
                'staff_count': df['担当者'].nunique(),
                'product_count': df['商品名'].nunique(),
                'customer_count': df['顧客名'].nunique(),
                'total_sales': df['売上金額'].sum(),
                'total_profit': df['粗利金額'].sum()
            }
            
            # データ品質チェック
            if df['売上金額'].min() < 0:
                validation_result['issues'].append("売上金額に負の値が含まれています")
            
            if df['粗利金額'].min() < 0:
                validation_result['issues'].append("粗利金額に負の値が含まれています")
            
            # 粗利率の妥当性チェック
            calculated_profit = df['売上金額'] - df['仕入れ金額']
            profit_diff = abs(df['粗利金額'] - calculated_profit)
            if (profit_diff > 1).any():  # 1円以上の差がある場合
                validation_result['issues'].append("粗利金額と売上金額-仕入れ金額に不一致があります")
            
            if validation_result['issues']:
                validation_result['is_valid'] = False
                
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"検証エラー: {str(e)}")
        
        return validation_result

class FilterManager:
    """フィルター管理クラス"""
    
    @staticmethod
    def apply_filters(df: pd.DataFrame, 
                     date_range: Optional[tuple] = None,
                     selected_staff: Optional[str] = None,
                     selected_product: Optional[str] = None,
                     selected_customer: Optional[str] = None) -> pd.DataFrame:
        """フィルターを適用する"""
        filtered_df = df.copy()
        
        # 期間フィルター
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df['売上年月'].dt.date >= start_date) &
                (filtered_df['売上年月'].dt.date <= end_date)
            ]
        
        # 担当者フィルター
        if selected_staff and selected_staff != '全て':
            filtered_df = filtered_df[filtered_df['担当者'] == selected_staff]
        
        # 商品フィルター
        if selected_product and selected_product != '全て':
            filtered_df = filtered_df[filtered_df['商品名'] == selected_product]
        
        # 顧客フィルター
        if selected_customer and selected_customer != '全て':
            filtered_df = filtered_df[filtered_df['顧客名'] == selected_customer]
        
        return filtered_df

class ChartManager:
    """チャート作成管理クラス"""
    
    @staticmethod
    def create_kpi_cards(filtered_df: pd.DataFrame) -> None:
        """KPIカードを作成する"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_sales = filtered_df['売上金額'].sum()
            st.metric("総売上金額", f"¥{total_sales:,}")
        
        with col2:
            total_profit = filtered_df['粗利金額'].sum()
            st.metric("総粗利金額", f"¥{total_profit:,}")
        
        with col3:
            profit_rate = (total_profit / total_sales * 100) if total_sales > 0 else 0
            st.metric("粗利率", f"{profit_rate:.1f}%")
        
        with col4:
            avg_sales = filtered_df['売上金額'].mean()
            st.metric("平均売上", f"¥{avg_sales:,.0f}")
    
    @staticmethod
    def format_currency(value: float) -> str:
        """通貨形式でフォーマットする"""
        return f"¥{value:,}"
    
    @staticmethod
    def format_percentage(value: float) -> str:
        """パーセンテージ形式でフォーマットする"""
        return f"{value:.1f}%"

class ConfigManager:
    """設定管理クラス"""
    
    @staticmethod
    def get_api_key() -> Optional[str]:
        """APIキーを取得する"""
        try:
            return st.secrets.get("API_KEY")
        except:
            return os.getenv("API_KEY")
    
    @staticmethod
    def get_llm_url() -> str:
        """LLM URLを取得する"""
        return os.getenv("LLM_URL", "https://api.openai.com")
    
    @staticmethod
    def validate_config() -> Dict[str, Any]:
        """設定の妥当性を検証する"""
        config_status = {
            'api_key_configured': bool(ConfigManager.get_api_key()),
            'llm_url_configured': bool(ConfigManager.get_llm_url()),
            'warnings': []
        }
        
        if not config_status['api_key_configured']:
            config_status['warnings'].append("APIキーが設定されていません")
        
        return config_status

# グローバルインスタンス
data_manager = DataManager() 