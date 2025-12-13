def codeblock_strip(text: str) -> str:
    if not text:
        return ""

    lines = text.strip().splitlines()
    if len(lines) <= 2:
        return text.strip()  # 太短则直接返回
    
    if lines[0].startswith("```") and lines[-1].startswith("```"):
        # 去除首尾行
        return "\n".join(lines[1:-1]).strip()
    return text.strip()


if __name__ == "__main__":
    sample_text = "```python\ndef fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        print(a)\n        a, b = b, a + b\n\nfibonacci(10)\n```"
    print("原始文本:")
    print(sample_text)
    print("\n去除Markdown后的文本:")
    print(codeblock_strip(sample_text))