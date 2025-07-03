import os
import streamlit as st
from typing import Dict, Any, Optional
import json

class AppConfig:
    """アプリケーション設定管理クラス"""
    
    # デフォルト設定
    DEFAULT_CONFIG = {
        'app_name': '売上ダッシュボード',
        'app_version': '2.0.0',
        'data_file': 'sales_test_data_utf8.csv',
        'llm_url': 'https://api.openai.com',
        'max_records_display': 1000,
        'cache_ttl': 3600,  # 1時間
        'chart_height': 600,
        'enable_ai_features': True,
        'enable_export': True,
        'enable_validation': True,
        'theme': {
            'primary_color': '#1f77b4',
            'secondary_color': '#ff7f0e',
            'background_color': '#f0f2f6',
            'text_color': '#262730'
        }
    }
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """設定を取得する"""
        config = cls.DEFAULT_CONFIG.copy()
        
        # 環境変数から設定を読み込み
        config.update({
            'llm_url': os.getenv('LLM_URL', config['llm_url']),
            'enable_ai_features': os.getenv('ENABLE_AI_FEATURES', 'true').lower() == 'true',
            'enable_export': os.getenv('ENABLE_EXPORT', 'true').lower() == 'true',
            'enable_validation': os.getenv('ENABLE_VALIDATION', 'true').lower() == 'true',
            'max_records_display': int(os.getenv('MAX_RECORDS_DISPLAY', config['max_records_display']))
        })
        
        return config
    
    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """APIキーを取得する"""
        # Streamlit secretsから取得
        try:
            return st.secrets.get("API_KEY")
        except:
            pass
        
        # 環境変数から取得
        return os.getenv("API_KEY")
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """設定の妥当性を検証する"""
        config = cls.get_config()
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'config': config
        }
        
        # APIキーの確認
        if config['enable_ai_features'] and not cls.get_api_key():
            validation_result['warnings'].append("AI機能が有効ですが、APIキーが設定されていません")
        
        # データファイルの確認
        if not os.path.exists(config['data_file']):
            validation_result['errors'].append(f"データファイルが見つかりません: {config['data_file']}")
            validation_result['is_valid'] = False
        
        # LLM URLの確認
        if not config['llm_url']:
            validation_result['warnings'].append("LLM URLが設定されていません")
        
        return validation_result
    
    @classmethod
    def save_config(cls, config: Dict[str, Any], file_path: str = 'app_config.json') -> bool:
        """設定をファイルに保存する"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"設定保存エラー: {e}")
            return False
    
    @classmethod
    def load_config(cls, file_path: str = 'app_config.json') -> Dict[str, Any]:
        """設定をファイルから読み込む"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"設定読み込みエラー: {e}")
        
        return cls.DEFAULT_CONFIG

class ThemeManager:
    """テーマ管理クラス"""
    
    @staticmethod
    def get_custom_css(config: Dict[str, Any]) -> str:
        """カスタムCSSを生成する"""
        theme = config.get('theme', {})
        
        return f"""
        <style>
            .main-header {{
                background: linear-gradient(90deg, {theme.get('primary_color', '#1f77b4')} 0%, {theme.get('secondary_color', '#ff7f0e')} 100%);
                padding: 1rem;
                border-radius: 10px;
                color: white;
                text-align: center;
                margin-bottom: 2rem;
            }}
            .metric-card {{
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                padding: 1rem;
                border-radius: 10px;
                border-left: 4px solid {theme.get('primary_color', '#1f77b4')};
                margin-bottom: 1rem;
            }}
            .analysis-section {{
                background: white;
                padding: 1.5rem;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 2rem;
            }}
            .loading-container {{
                display: flex;
                justify-content: center;
                align-items: center;
                height: 200px;
                background: {theme.get('background_color', '#f0f2f6')};
                border-radius: 10px;
                margin: 20px 0;
            }}
            .error-container {{
                background: #ffebee;
                border: 1px solid #f44336;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                color: #c62828;
            }}
            .success-container {{
                background: #e8f5e8;
                border: 1px solid #4caf50;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                color: #2e7d32;
            }}
            .stButton > button {{
                width: 100%;
                border-radius: 8px;
                font-weight: 500;
                margin-bottom: 0.5rem;
            }}
            .stSelectbox > div > div {{
                border-radius: 8px;
            }}
            .stDateInput > div > div {{
                border-radius: 8px;
            }}
        </style>
        """

class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """計測開始"""
        import time
        self.start_time = time.time()
    
    def end(self):
        """計測終了"""
        import time
        self.end_time = time.time()
    
    def get_elapsed_time(self) -> float:
        """経過時間を取得"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_memory_usage(self) -> str:
        """メモリ使用量を取得"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return f"{memory_mb:.1f} MB"
        except ImportError:
            return "N/A"
    
    def log_performance(self, operation: str):
        """パフォーマンスをログに記録"""
        elapsed = self.get_elapsed_time()
        memory = self.get_memory_usage()
        
        print(f"パフォーマンス - {operation}: {elapsed:.2f}秒, メモリ: {memory}")
        
        # Streamlitのセッション状態に保存
        if 'performance_log' not in st.session_state:
            st.session_state.performance_log = []
        
        st.session_state.performance_log.append({
            'operation': operation,
            'elapsed_time': elapsed,
            'memory_usage': memory,
            'timestamp': st.session_state.get('timestamp', 'N/A')
        }) 