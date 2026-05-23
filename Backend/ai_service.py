# -*- coding: utf-8 -*-
"""
AI 分析服务模块 - 使用硅基流动（SiliconFlow）API

该模块提供基于 LangChain 的 AI 分析功能，包括：
- 基金深度分析
- 市场趋势分析
- 板块机会分析
- 风险提示分析

支持的 LLM 提供商：
- 硅基流动（SiliconFlow）- 推荐
- DeepSeek
- 通义千问
- 智谱AI
- OpenAI 兼容 API
"""

import os
import re
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class AIService:
    """AI 分析服务类"""
    
    def __init__(self):
        """初始化 AI 服务"""
        self.llm = None
        self._api_key = os.getenv("LLM_API_KEY", "")
        self._api_base = os.getenv("LLM_API_BASE", "https://api.siliconflow.cn/v1")
        self._model = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    
    def is_available(self) -> bool:
        """检查 AI 服务是否可用"""
        return bool(self._api_key)
    
    def _init_llm(self, fast_mode: bool = False):
        """
        初始化 LangChain LLM
        
        Args:
            fast_mode: 是否为快速模式（调整超时参数）
        """
        try:
            from langchain_openai import ChatOpenAI
            
            if not self._api_key:
                print("未配置 LLM_API_KEY 环境变量")
                return None
            
            # 根据模式调整参数
            temperature = 0.3 if fast_mode else 0.2
            timeout = 60 if fast_mode else 120
            
            llm = ChatOpenAI(
                model=self._model,
                openai_api_key=self._api_key,
                openai_api_base=self._api_base,
                temperature=temperature,
                request_timeout=timeout
            )
            
            return llm
            
        except ImportError:
            print("请安装 langchain-openai: pip install langchain-openai")
            return None
        except Exception as e:
            print(f"初始化 LLM 失败: {e}")
            return None
    
    def _call_llm_simple(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """
        简单调用 LLM（不使用 LangChain，直接使用 OpenAI SDK）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            
        Returns:
            LLM 返回的文本
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self._api_key,
                base_url=self._api_base
            )
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.3,
                max_tokens=4096
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            print("请安装 openai: pip install openai")
            return None
        except Exception as e:
            print(f"调用 LLM 失败: {e}")
            return None
    
    def analyze_fund(self, fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 AI 分析基金
        
        Args:
            fund_data: 基金数据，包含 basic_info, performance, portfolio 等
            
        Returns:
            分析结果字典
        """
        if not self.is_available():
            return {"error": "AI 服务未配置，请检查 LLM_API_KEY 环境变量"}
        
        try:
            # 构建分析提示
            prompt = self._build_fund_analysis_prompt(fund_data)
            
            system_prompt = """你是一位资深基金分析师，擅长基金投资分析和风险评估。
请基于提供的基金数据，给出专业、客观、全面的分析报告。

**重要提示**：
1. 请务必根据提供的基金数据（业绩、风险、持仓等）进行真实评估，**绝对不要**直接抄袭示例中的数值。
2. sentiment_score 必须根据基金的实际表现计算（0-100），反映其投资价值。
3. operation_advice 必须基于你的分析结论给出。

**输出要求**：
请严格按照以下 JSON 格式输出，不要添加任何其他内容：
```json
{
    "sentiment_score": 0-100 分，反映基金的投资价值，0 表示非常差，100 表示非常好，50 表示一般，
    "operation_advice": "强烈推荐"/"建议买入"/"持有观望"/"建议减仓"/"建议卖出"，
    "summary": "详细的分析总结，包含业绩、风险、经理等维度的综合评价（200-300字）",
    "dashboard": {
        "performance_eval": "优秀/良好/一般/较差",
        "manager_ability": "优秀/良好/一般/较差",
        "position_analysis": "集中/均衡/分散",
        "market_outlook": "乐观/中性/谨慎"
    },
    "highlights": ["亮点1", "亮点2", "亮点3"],
    "risk_factors": ["风险1", "风险2", "风险3"],
    "news_intel": ["相关市场信息1", "相关市场信息2"],
    "detailed_report": "Markdown格式的详细深度分析报告，包含：1. 业绩归因分析；2. 风险收益特征；3. 经理管理风格；4. 后市策略建议。请使用二级和三级标题组织内容。"
}
```

**评分说明**：
- sentiment_score: 0-100 分，越高表示越值得投资
- operation_advice: 可选值为 "强烈推荐"、"建议买入"、"持有观望"、"建议减仓"、"建议卖出"
- detailed_report: 请提供不少于500字的深度分析，使用 Markdown 格式
"""
            
            # 调用 LLM
            result = self._call_llm_simple(prompt, system_prompt)
            
            if not result:
                return {"error": "AI 分析失败，请稍后重试"}
            
            # 解析结果
            return self._parse_fund_analysis_result(result)
            
        except Exception as e:
            print(f"基金分析出错: {e}")
            return {"error": f"分析过程出错: {str(e)}"}
    
    def _build_fund_analysis_prompt(self, fund_data: Dict[str, Any]) -> str:
        """构建基金分析提示"""
        basic_info = fund_data.get('basic_info', {})
        performance = fund_data.get('performance', {})
        portfolio = fund_data.get('portfolio', {})
        fund_managers = fund_data.get('fund_managers', [])
        risk_metrics = fund_data.get('risk_metrics', {})
        realtime = fund_data.get('realtime_estimate', {})
        
        prompt = f"""请分析以下基金：

## 基本信息
- 基金名称：{basic_info.get('fund_name', '未知')}
- 基金代码：{basic_info.get('fund_code', '未知')}
- 基金类型：{basic_info.get('fund_type', '未知')}
- 申购费率：{basic_info.get('current_rate', '未知')}%

## 业绩表现
- 近1月收益：{performance.get('1_month_return', '未知')}%
- 近3月收益：{performance.get('3_month_return', '未知')}%
- 近6月收益：{performance.get('6_month_return', '未知')}%
- 近1年收益：{performance.get('1_year_return', '未知')}%

## 实时估值
- 估算净值：{realtime.get('estimate_value', '未知')}
- 估算涨跌：{realtime.get('estimate_change', '未知')}%
- 估值时间：{realtime.get('estimate_time', '未知')}
"""
        
        # 添加业绩走势数据
        total_return_trend = fund_data.get('total_return_trend', [])
        if total_return_trend:
            prompt += "\n## 业绩走势（累计收益率，近3年月度采样）\n"
            for series in total_return_trend:
                name = series.get('name', '未知')
                data = series.get('data', [])
                if not data: continue
                
                prompt += f"### {name}\n"
                sorted_data = sorted(data, key=lambda x: x.get('date', ''))
                sampled_points = []
                seen_months = set()
                
                for point in reversed(sorted_data):
                    date_str = point.get('date', '')
                    if not date_str: continue
                    month = date_str[:7]
                    if month not in seen_months:
                        sampled_points.insert(0, point)
                        seen_months.add(month)
                        if len(sampled_points) >= 36: break
                
                for p in sampled_points:
                    prompt += f"- {p.get('date')}: {p.get('value')}%\n"
        
        # 添加风险指标
        if risk_metrics:
            prompt += f"""
## 风险指标
- 夏普比率：{risk_metrics.get('sharpe_ratio', '未知')}
- 最大回撤：{risk_metrics.get('max_drawdown', '未知')}%
- 年化波动率：{risk_metrics.get('volatility', '未知')}%
"""
        
        # 添加基金经理信息
        if fund_managers:
            manager = fund_managers[0]
            prompt += f"""
## 基金经理
- 姓名：{manager.get('name', '未知')}
- 从业年限：{manager.get('work_experience', '未知')}
- 管理规模：{manager.get('managed_fund_size', '未知')}
"""
        
        # 添加持仓信息
        stock_codes = portfolio.get('stock_codes', [])
        if stock_codes:
            prompt += "\n## 重仓股票（前10）\n"
            for i, stock in enumerate(stock_codes[:10], 1):
                if isinstance(stock, dict):
                    prompt += f"{i}. {stock.get('name', '未知')} ({stock.get('code', '')})\n"
                else:
                    prompt += f"{i}. {stock}\n"
        
        prompt += "\n请基于以上数据，给出全面的投资分析。"
        
        return prompt
    
    def _parse_fund_analysis_result(self, result: str) -> Dict[str, Any]:
        """解析基金分析结果"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = result.strip()
                if json_str.startswith('{'):
                    pass
                else:
                    # 尝试找到 JSON 开始位置
                    start = json_str.find('{')
                    end = json_str.rfind('}')
                    if start != -1 and end != -1:
                        json_str = json_str[start:end+1]
            
            data = json.loads(json_str)
            
            # 验证必要字段
            required_fields = ['sentiment_score', 'operation_advice', 'summary', 
                             'dashboard', 'highlights', 'risk_factors', 'detailed_report']
            for field in required_fields:
                if field not in data:
                    data[field] = self._get_default_value(field)
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            # 返回默认结构
            return {
                "sentiment_score": 50,
                "operation_advice": "持有观望",
                "summary": result[:200] if result else "分析结果解析失败",
                "dashboard": {
                    "performance_eval": "一般",
                    "manager_ability": "一般",
                    "position_analysis": "均衡",
                    "market_outlook": "中性"
                },
                "highlights": ["数据分析中"],
                "risk_factors": ["请谨慎投资"],
                "news_intel": [],
                "detailed_report": result if result else "暂无详细分析"
            }
    
    def _get_default_value(self, field: str) -> Any:
        """获取字段默认值"""
        defaults = {
            'sentiment_score': 50,
            'operation_advice': '持有观望',
            'summary': '暂无分析',
            'dashboard': {
                "performance_eval": "一般",
                "manager_ability": "一般",
                "position_analysis": "均衡",
                "market_outlook": "中性"
            },
            'highlights': [],
            'risk_factors': [],
            'news_intel': [],
            'detailed_report': '暂无详细分析报告'
        }
        return defaults.get(field, None)
    
    def generate_market_summary(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成每日市场行情摘要
        
        Args:
            market_data: 市场数据，包含指数、板块、快讯等
            
        Returns:
            市场分析摘要
        """
        if not self.is_available():
            return {"error": "AI 服务未配置，请检查 LLM_API_KEY 环境变量"}
        
        try:
            prompt = self._build_market_summary_prompt(market_data)
            
            system_prompt = """你是一位资深金融分析师，擅长宏观市场分析和趋势判断。
请基于提供的市场数据，给出专业、简洁的市场分析摘要。

**重要提示**：
请务必根据提供的市场数据（指数、板块、资讯等）进行真实评估，**绝对不要**直接抄袭示例中的数值。sentiment_score 必须根据市场实际表现计算（0-100）。

**输出要求**：
请严格按照以下 JSON 格式输出：
```json
{
    "market_sentiment": "乐观/中性/谨慎/悲观",
    "sentiment_score": 58,
    "summary": "一段话总结今日市场走势和关键信息（100-150字）",
    "key_points": ["要点1", "要点2", "要点3"],
    "hot_sectors": ["热门板块1", "热门板块2"],
    "risk_alerts": ["风险提示1", "风险提示2"],
    "operation_suggestion": "短期操作建议（50字内）"
}
```
"""
            
            result = self._call_llm_simple(prompt, system_prompt)
            
            if not result:
                return {"error": "市场分析失败，请稍后重试"}
            
            return self._parse_market_summary_result(result)
            
        except Exception as e:
            print(f"市场分析出错: {e}")
            return {"error": f"分析过程出错: {str(e)}"}
    
    def _build_market_summary_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建市场分析提示"""
        prompt = f"请分析以下市场数据（{datetime.now().strftime('%Y-%m-%d %H:%M')}）：\n\n"
        
        # 添加市场指数
        indices = market_data.get('indices', [])
        if indices:
            prompt += "## 主要指数\n"
            for idx in indices[:10]:
                if isinstance(idx, dict):
                    prompt += f"- {idx.get('name', '')}: {idx.get('price', '')} ({idx.get('change', '')})\n"
                elif isinstance(idx, (list, tuple)):
                    prompt += f"- {idx[0]}: {idx[1]} ({idx[2] if len(idx) > 2 else ''})\n"
        
        # 添加板块数据
        sectors = market_data.get('sectors', [])
        if sectors:
            prompt += "\n## 领涨板块\n"
            for sec in sectors[:5]:
                if isinstance(sec, dict):
                    prompt += f"- {sec.get('name', '')}: {sec.get('change', '')}\n"
                elif isinstance(sec, (list, tuple)):
                    prompt += f"- {sec[0]}: {sec[1]}\n"
        
        # 添加快讯
        news = market_data.get('news', [])
        if news:
            prompt += "\n## 重要快讯\n"
            for n in news[:5]:
                if isinstance(n, dict):
                    prompt += f"- {n.get('title', n.get('content', ''))}\n"
                else:
                    prompt += f"- {n}\n"
        
        prompt += "\n请基于以上数据，给出市场分析摘要。"
        
        return prompt
    
    def _parse_market_summary_result(self, result: str) -> Dict[str, Any]:
        """解析市场分析结果"""
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result.strip()
                start = json_str.find('{')
                end = json_str.rfind('}')
                if start != -1 and end != -1:
                    json_str = json_str[start:end+1]
            
            return json.loads(json_str)
            
        except json.JSONDecodeError:
            return {
                "market_sentiment": "中性",
                "sentiment_score": 50,
                "summary": result[:300] if result else "分析结果解析失败",
                "key_points": [],
                "hot_sectors": [],
                "risk_alerts": [],
                "operation_suggestion": "请关注市场变化"
            }


    def analyze_position_advice(self, fund_data: Dict[str, Any], position: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于持仓情况，使用 AI 分析当前应加仓、减仓还是持有

        Args:
            fund_data: 基金数据，包含 basic_info, performance, net_worth_trend, realtime_estimate 等
            position: 持仓数据，包含 cost, shares, purchase_date, purchase_time 等

        Returns:
            分析结果字典
        """
        if not self.is_available():
            return {"error": "AI 服务未配置"}

        try:
            prompt = self._build_position_advice_prompt(fund_data, position)

            system_prompt = """你是一位资深基金投资顾问，精通中国公募基金交易规则和持仓管理策略。

**中国基金交易规则要点（必须牢记）**：
1. T日15:00前申购/赎回，按T日净值确认；15:00后按T+1日净值
2. 基金实行T+1确认制度，当日买入次日才能查看确认份额
3. 持有不足7天赎回有1.5%惩罚性赎回费
4. 场外基金净值每日公布一次（通常在晚间20:00-22:00）
5. 交易日为周一至周五（法定节假日除外）
6. 基金分红方式：现金分红和红利再投资

**分析要点**：
- 结合用户的成本价、持有时间、盈亏状况分析
- 考虑当前市场估值水平和基金近期走势
- 注意区分交易时间和非交易时间的操作建议
- 如果用户持有不足7天，赎回建议要特别谨慎

**输出格式（严格JSON，不要任何额外内容）**：
```json
{
    "action": "强烈加仓"/"适度加仓"/"持有观望"/"逐步减仓"/"清仓卖出",
    "action_type": "buy"/"hold"/"sell",
    "confidence": 0-100,
    "summary": "一句话总结建议理由（30字内）",
    "reason": "详细分析理由（100-150字），包含：1.当前估值位置判断；2.盈亏状态分析；3.交易规则考量（如持有天数、15:00节点等）；4.风险提示",
    "key_points": ["关键分析点1", "关键分析点2", "关键分析点3"]
}
```

**action 判断参考**：
- 当前净值处于近60日低位（低于20%分位）且亏损超过5% → 强烈加仓
- 当前净值处于近60日中低位（20%-35%分位）→ 适度加仓
- 处于中位区域（35%-65%）盈亏不大 → 持有观望
- 获利超过15%且净值处于高位 → 逐步减仓
- 获利超过30%或净值处于极高位置 → 清仓卖出

注意：以上仅为参考框架，请结合具体数据灵活判断，不要机械套用。"""
            result = self._call_llm_simple(prompt, system_prompt)

            if not result:
                return {"error": "AI 分析失败，请稍后重试"}

            return self._parse_position_advice_result(result)

        except Exception as e:
            print(f"持仓建议分析出错: {e}")
            return {"error": f"分析出错: {str(e)}"}

    def _build_position_advice_prompt(self, fund_data: Dict[str, Any], position: Dict[str, Any]) -> str:
        """构建持仓建议分析提示"""
        basic_info = fund_data.get('basic_info', {})
        performance = fund_data.get('performance', {})
        realtime = fund_data.get('realtime_estimate', {})
        risk_metrics = fund_data.get('risk_metrics', {})
        net_worth_trend = fund_data.get('net_worth_trend', [])

        from datetime import datetime, timezone, timedelta
        CHINA_TZ = timezone(timedelta(hours=8))
        now = datetime.now(CHINA_TZ)
        today_str = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        is_trading_day = now.weekday() < 5  # 简单判断，不考虑节假日
        is_before_1500 = current_time < '15:00'

        prompt = f"""当前时间：{today_str} {current_time}（{'交易日，' + ('15:00前' if is_before_1500 else '15:00后') if is_trading_day else '非交易日'}）

## 基金信息
- 名称：{basic_info.get('fund_name', '未知')}
- 代码：{basic_info.get('fund_code', '未知')}
- 类型：{basic_info.get('fund_type', '未知')}
- 费率：{basic_info.get('current_rate', '未知')}%

## 实时估值
- 估算净值：{realtime.get('estimate_value', '未知')}
- 估算涨跌幅：{realtime.get('estimate_change', '未知')}%
- 估值时间：{realtime.get('estimate_time', '未知')}
- 最新单位净值：{realtime.get('net_worth', '未知')}
- 净值日期：{realtime.get('net_worth_date', '未知')}

## 业绩表现
- 近1月：{performance.get('1_month_return', '未知')}%
- 近3月：{performance.get('3_month_return', '未知')}%
- 近6月：{performance.get('6_month_return', '未知')}%
- 近1年：{performance.get('1_year_return', '未知')}%
"""

        # 风险指标
        if risk_metrics:
            prompt += f"""
## 风险指标
- 近1年夏普比率：{risk_metrics.get('sharpe_ratio_1y', '未知')}
- 近1年最大回撤：{risk_metrics.get('max_drawdown_1y', '未知')}%
- 近1年年化波动率：{risk_metrics.get('volatility_1y', '未知')}%
- 近1年年化收益：{risk_metrics.get('annual_return_1y', '未知')}%
"""

        # 近期走势摘要
        if net_worth_trend:
            sorted_trend = sorted(
                [t for t in net_worth_trend if t.get('date') and t.get('net_worth') is not None],
                key=lambda x: x['date']
            )
            if len(sorted_trend) >= 5:
                recent = sorted_trend[-10:]
                prompt += "\n## 近10个交易日净值走势\n"
                for p in recent:
                    prompt += f"- {p['date']}: {p['net_worth']}\n"

                # 60日高低点
                recent60 = sorted_trend[-60:] if len(sorted_trend) >= 60 else sorted_trend
                vals = [float(t['net_worth']) for t in recent60]
                prompt += f"\n近{len(recent60)}日最高净值: {max(vals)}, 最低净值: {min(vals)}"
                if realtime.get('estimate_value'):
                    cur = float(realtime['estimate_value'])
                    pos_pct = round((cur - min(vals)) / (max(vals) - min(vals)) * 100, 1) if max(vals) > min(vals) else 50
                    prompt += f"\n当前净值在近{len(recent60)}日区间位置: {pos_pct}%（0%为最低点，100%为最高点）"

        # 持仓信息
        purchase_date = position.get('purchase_date', '未知')
        purchase_time = position.get('purchase_time', '15:00')
        cost = float(position.get('cost', 0))
        shares = float(position.get('shares', 0))
        cost_amount = cost * shares

        cur_nav = float(realtime.get('estimate_value') or realtime.get('net_worth') or cost)
        market_value = shares * cur_nav
        profit = market_value - cost_amount
        profit_rate = (profit / cost_amount * 100) if cost_amount > 0 else 0

        # 计算持有天数
        try:
            purchase_dt = datetime.strptime(purchase_date, '%Y-%m-%d')
            hold_days = (now - purchase_dt.replace(tzinfo=CHINA_TZ)).days
        except:
            hold_days = -1

        prompt += f"""
## 我的持仓
- 买入日期：{purchase_date}
- 买入时间：{purchase_time}（{'15:00前' if purchase_time < '15:00' else '15:00后'}）
- 成本净值：{cost}
- 持有份额：{shares:.2f}
- 持仓成本：¥{cost_amount:.2f}
- 当前市值：¥{market_value:.2f}
- 浮动盈亏：¥{profit:.2f}（{profit_rate:+.2f}%）
- 已持有天数：{hold_days}天
"""

        if hold_days > 0 and hold_days < 7:
            prompt += "\n⚠️ 注意：持有不足7天，赎回将产生1.5%惩罚性赎回费！"

        prompt += f"""
---
请基于以上数据，结合当前时间（{today_str} {current_time}，{'交易日' if is_trading_day else '非交易日'}），给出专业的持仓操作建议。"""

        return prompt

    def _parse_position_advice_result(self, result: str) -> Dict[str, Any]:
        """解析持仓建议分析结果"""
        import re, json
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result.strip()
                start = json_str.find('{')
                end = json_str.rfind('}')
                if start != -1 and end != -1:
                    json_str = json_str[start:end+1]

            data = json.loads(json_str)
            return {
                "action": data.get("action", "持有观望"),
                "action_type": data.get("action_type", "hold"),
                "confidence": data.get("confidence", 50),
                "summary": data.get("summary", "无法生成建议"),
                "reason": data.get("reason", ""),
                "key_points": data.get("key_points", [])
            }
        except:
            return {
                "action": "持有观望",
                "action_type": "hold",
                "confidence": 30,
                "summary": "AI分析结果解析失败",
                "reason": result[:300] if result else "",
                "key_points": []
            }


# 单例实例
_ai_service_instance: Optional[AIService] = None

def get_ai_service() -> AIService:
    """获取 AI 服务单例"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance
