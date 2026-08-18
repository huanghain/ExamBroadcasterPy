"""
智谱 GLM-4-Flash AI 服务

通过 OpenAI 兼容接口调用智谱 API：
- Base URL: https://open.bigmodel.cn/api/paas/v4
- 支持 Chat Completions + Function Calling (tools)
"""
import json
import re
import httpx
from typing import Optional
from datetime import datetime

from config import AI_BASE_URL, AI_MODEL
from models.parsed_row import ParsedExamRow


class AIResponseValidator:
    """AI 响应校验器"""

    @staticmethod
    def is_valid_json(text: str) -> bool:
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    @staticmethod
    def extract_json_from_text(text: str) -> str | None:
        """从混合文本中提取 JSON 片段"""
        if not text:
            return None
        # 尝试匹配数组
        match = re.search(r"\[[\s\S]*\]", text)
        if match and AIResponseValidator.is_valid_json(match.group()):
            return match.group()
        # 尝试匹配对象
        match = re.search(r"\{[\s\S]*\}", text)
        if match and AIResponseValidator.is_valid_json(match.group()):
            return match.group()
        return None

    @staticmethod
    def normalize_time(time_str: str) -> str:
        """标准化时间格式"""
        cleaned = time_str.strip()
        for p in ["上午", "下午", "AM", "PM", "am", "pm"]:
            cleaned = cleaned.replace(p, "")
        cleaned = cleaned.replace("点", ":").replace("时", ":")
        cleaned = cleaned.replace("分", "").replace("秒", "").strip()

        parts = cleaned.split(":")
        if len(parts) >= 2:
            try:
                h, m = int(parts[0]), int(parts[1])
                return f"{h:02d}:{m:02d}"
            except ValueError:
                pass
        return time_str

    @staticmethod
    def attempt_fix(row: ParsedExamRow) -> ParsedExamRow:
        """尝试自动修正解析结果"""
        if row.date:
            try:
                dt = datetime.strptime(row.date.strip(), "%Y-%m-%d")
                row.date = dt.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    dt = datetime.fromisoformat(row.date.strip())
                    row.date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        if row.start_time:
            row.start_time = AIResponseValidator.normalize_time(row.start_time)
        if row.end_time:
            row.end_time = AIResponseValidator.normalize_time(row.end_time)

        return row

    @staticmethod
    def fallback_parse(raw_text: str) -> list[ParsedExamRow]:
        """规则引擎兜底解析"""
        results = []
        if not raw_text:
            return results

        for line in raw_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # 模式1: "科目 日期 开始-结束"
            m = re.match(
                r"^(.+?)\s+(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)\s+"
                r"(\d{1,2}[:\s]\d{2})\s*[-~至到]\s*(\d{1,2}[:\s]\d{2})\s*(.*)$",
                line,
            )
            if m:
                results.append(ParsedExamRow(
                    subject=m.group(1).strip(),
                    date=m.group(2).strip(),
                    start_time=m.group(3).strip(),
                    end_time=m.group(4).strip(),
                    confidence=0.5,
                    parse_warning="使用规则引擎降级解析，请人工复核",
                ))
                continue

            # 模式2: 分隔符格式
            for sep in ["|", "\t", ","]:
                if sep in line:
                    parts = [p.strip() for p in line.split(sep)]
                    if len(parts) >= 4:
                        results.append(ParsedExamRow(
                            subject=parts[0], date=parts[1],
                            start_time=parts[2], end_time=parts[3],
                            confidence=0.5,
                            parse_warning="使用规则引擎降级解析，请人工复核",
                        ))
                        break

        return results


class ZhipuAIService:
    """智谱 GLM-4-Flash AI 服务"""

    def __init__(self, api_key: str, model: str = AI_MODEL, base_url: str = AI_BASE_URL):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._validator = AIResponseValidator()
        self._client = httpx.Client(timeout=30.0)

    def __del__(self):
        """析构时确保关闭 httpx 客户端"""
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _call_api(self, messages: list[dict], tools: list | None = None,
                  max_retries: int = 2) -> dict:
        """调用 API（带重试）"""
        body = {"model": self._model, "messages": messages}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                resp = self._client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"API 返回错误 {resp.status_code}: {resp.text}")
                return resp.json()
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < max_retries:
                    import time
                    time.sleep(2 * (attempt + 1))
            except RuntimeError:
                raise

        raise RuntimeError(f"API 调用失败，已重试 {max_retries} 次: {last_error}")

    def parse_table(self, file_content: str, file_name: str) -> list[ParsedExamRow]:
        """解析表格文件"""
        system_prompt = (
            "你是一个表格解析助手。用户会提供一份包含考试安排的表格数据。\n"
            "你需要返回一个JSON数组，每个元素包含字段：Subject, Date(yyyy-MM-dd),\n"
            "StartTime(HH:mm), EndTime(HH:mm)。\n"
            "如果表格中包含[科目][时间]等任何语言变体，请自动识别。\n"
            "若某字段无法识别，返回null。不要添加额外解释。\n"
            "请始终使用工具调用（parse_exam_schedule）来返回结果。"
        )

        tools = [{
            "type": "function",
            "function": {
                "name": "parse_exam_schedule",
                "description": "解析考试安排表格",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exams": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "subject": {"type": "string"},
                                    "date": {"type": "string"},
                                    "start_time": {"type": "string"},
                                    "end_time": {"type": "string"},
                                },
                                "required": ["subject", "date", "start_time", "end_time"]
                            },
                        }
                    },
                },
            },
        }]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"以下是考试安排表格数据（文件名：{file_name}）：\n{file_content}"},
        ]

        response = self._call_api(messages, tools)
        results = self._parse_tool_call_response(response)

        if not results:
            results = self._validator.fallback_parse(file_content)

        return self._validate_and_fix(results)

    def parse_natural_language(self, text: str) -> ParsedExamRow:
        """解析自然语言考试信息"""
        system_prompt = (
            "你是一个考试安排助手。用户会用自然语言描述一场考试的信息。\n"
            "请提取考试科目、开始时间、结束时间等信息。\n"
            "如果用户提到了模板关键词（如[高考][四六级][期末]），也请提取。\n"
            "请使用工具调用（add_exam_from_natural_language）返回结果。\n"
            f"当前日期是：{datetime.now().strftime('%Y-%m-%d %A')}"
        )

        tools = [{
            "type": "function",
            "function": {
                "name": "add_exam_from_natural_language",
                "description": "解析用户输入的自然语言考试信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "考试科目"},
                        "start_datetime": {"type": "string", "description": "开始时间(yyyy-MM-ddTHH:mm:ss)"},
                        "end_datetime": {"type": "string", "description": "结束时间(yyyy-MM-ddTHH:mm:ss)"},
                        "template_keyword": {"type": "string"},
                    },
                    "required": ["subject", "start_datetime", "end_datetime"],
                },
            },
        }]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        response = self._call_api(messages, tools)
        args_str = self._extract_tool_call_args(response)

        if args_str:
            args = json.loads(args_str)
            start_dt = args.get("start_datetime", "")
            end_dt = args.get("end_datetime", "")

            return ParsedExamRow(
                subject=args.get("subject"),
                date=start_dt.split("T")[0] if "T" in start_dt else start_dt[:10],
                start_time=start_dt.split("T")[1][:5] if "T" in start_dt else None,
                end_time=end_dt.split("T")[1][:5] if "T" in end_dt else None,
                confidence=0.9,
            )

        raise RuntimeError("AI 未能解析自然语言输入，请尝试更明确的描述")

    def process_command(self, command: str, context: str) -> str:
        """智能助手命令处理"""
        messages = [
            {"role": "system", "content": f"你是考试广播系统的智能助手。\n当前系统中的考试信息如下：\n{context}"},
            {"role": "user", "content": command},
        ]
        response = self._call_api(messages)
        return self._extract_text_content(response) or "抱歉，我无法处理您的请求。"

    def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            messages = [{"role": "user", "content": "你好，请回复'连接成功'"}]
            response = self._call_api(messages, max_retries=0)
            return bool(self._extract_text_content(response))
        except Exception:
            return False

    # ---- 内部辅助方法 ----

    def _parse_tool_call_response(self, response: dict) -> list[ParsedExamRow]:
        results = []
        try:
            choices = response.get("choices", [])
            if not choices:
                return results
            msg = choices[0].get("message", {})
            if msg.get("finish_reason") == "tool_calls":
                for tc in msg.get("tool_calls", []):
                    func = tc.get("function", {})
                    if func.get("name") == "parse_exam_schedule":
                        args = json.loads(func.get("arguments", "{}"))
                        for exam in args.get("exams", []):
                            results.append(ParsedExamRow(
                                subject=exam.get("subject"),
                                date=exam.get("date"),
                                start_time=exam.get("start_time"),
                                end_time=exam.get("end_time"),
                                confidence=0.95,
                            ))
        except Exception as e:
            print(f"解析 tool_calls 失败: {e}")
        return results

    def _extract_tool_call_args(self, response: dict) -> str | None:
        try:
            choices = response.get("choices", [])
            if not choices:
                return None
            msg = choices[0].get("message", {})
            for tc in msg.get("tool_calls", []):
                return tc.get("function", {}).get("arguments")
        except Exception:
            pass
        return None

    def _extract_text_content(self, response: dict) -> str | None:
        try:
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content")
        except Exception:
            pass
        return None

    def _validate_and_fix(self, rows: list[ParsedExamRow]) -> list[ParsedExamRow]:
        validated = []
        for row in rows:
            fixed = self._validator.attempt_fix(row)
            if not fixed.has_missing_fields:
                validated.append(fixed)
            else:
                missing = fixed.get_missing_field_names()
                fixed.parse_warning = f"缺失字段: {', '.join(missing)}"
                validated.append(fixed)
        return validated

    def close(self):
        """关闭 httpx 客户端，释放连接"""
        if self._client and not self._client.is_closed:
            self._client.close()
