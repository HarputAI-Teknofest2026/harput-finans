import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import requests


# =========================================================
# CONFIG
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://127.0.0.1:11434",
).rstrip("/")

OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

REQUEST_TIMEOUT = 240
CODE_TIMEOUT = 5

MAX_RETRIES = 3


# =========================================================
# OUTPUT FIELDS
# =========================================================

FIELDS = [
    "kar_payi_orani",
    "finansman_orani",
    "finansman_tutari",
    "vade",
    "taksit_sayisi",
    "masraf_bilgisi",
    "hedef_kitle",
    "para_birimi",
    "kosullar",
]


# =========================================================
# CODE SAFETY
# =========================================================

SAFE_BUILTIN_CALLS = {
    "str",
    "int",
    "float",
    "list",
    "dict",
    "set",
    "tuple",
    "len",
    "range",
    "enumerate",
    "zip",
    "sorted",
    "min",
    "max",
    "any",
    "all",
    "isinstance",
}


SAFE_METHOD_CALLS = {
    "append",
    "extend",
    "insert",
    "count",
    "index",

    "get",
    "items",
    "keys",
    "values",
    "setdefault",

    "add",

    "strip",
    "lstrip",
    "rstrip",
    "lower",
    "upper",
    "casefold",
    "replace",
    "split",
    "rsplit",
    "join",
    "startswith",
    "endswith",

    "group",
    "groups",
    "groupdict",
    "span",
    "start",
    "end",

    "search",
    "match",
    "fullmatch",
    "findall",
    "finditer",
    "split",
    "sub",
    "subn",
}


SAFE_RE_CALLS = {
    "compile",
    "search",
    "match",
    "fullmatch",
    "findall",
    "finditer",
    "split",
    "sub",
    "subn",
    "escape",
}


SAFE_RE_ATTRIBUTES = (
    SAFE_RE_CALLS
    | {
        "IGNORECASE",
        "MULTILINE",
        "DOTALL",
        "VERBOSE",
        "I",
        "M",
        "S",
        "X",
    }
)


DANGEROUS_NAMES = {
    "open",
    "exec",
    "eval",
    "compile",
    "__import__",
    "input",
    "globals",
    "locals",
    "vars",
    "dir",
    "help",
    "breakpoint",
    "getattr",
    "setattr",
    "delattr",
    "memoryview",

    "os",
    "sys",
    "subprocess",
    "pathlib",
    "socket",
    "requests",
    "urllib",
    "shutil",
}


DISALLOWED_NODES = (
    ast.ImportFrom,
    ast.ClassDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Raise,
    ast.Global,
    ast.Nonlocal,
    ast.Delete,
    ast.While,
    ast.Yield,
    ast.YieldFrom,
    ast.Await,
)


# =========================================================
# TEXT HELPERS
# =========================================================

def clean_text(value):
    value = str(value or "")

    value = value.replace(
        "\xa0",
        " ",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_for_compare(value):
    return clean_text(
        value
    ).casefold()


def normalize_semantic(value):
    value = clean_text(
        value
    ).casefold()

    value = value.rstrip(
        ".,;:"
    )

    return value.strip()


def unique_strings(values):
    result = []
    seen = set()

    for value in values:

        cleaned = clean_text(
            value
        )

        normalized = normalize_semantic(
            cleaned
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        result.append(
            cleaned
        )

    return result


# =========================================================
# OLLAMA
# =========================================================

def get_available_models():
    try:
        response = requests.get(
            OLLAMA_TAGS_URL,
            timeout=15,
        )

        response.raise_for_status()

    except Exception as error:
        raise RuntimeError(
            (
                "Ollama'ya bağlanılamadı.\n"
                f"URL: {OLLAMA_TAGS_URL}\n"
                f"Hata: {error}\n\n"
                "Ollama kapalıysa başka terminalde:\n"
                "ollama serve"
            )
        )

    payload = response.json()

    models = []

    for item in payload.get(
        "models",
        [],
    ):
        name = item.get(
            "name"
        )

        if name:
            models.append(
                name
            )

    return models


def choose_model(
    available_models,
    requested_model=None,
):
    if requested_model:

        requested_cf = (
            requested_model
            .casefold()
        )

        for model in available_models:

            if (
                model.casefold()
                == requested_cf
            ):
                return model

        return requested_model

    if not available_models:
        raise RuntimeError(
            (
                "Ollama çalışıyor fakat "
                "kurulu model bulunamadı."
            )
        )

    priorities = [
        "qwen2.5-coder:14b",
        "qwen2.5-coder:7b",
        "qwen3-coder",
        "qwen2.5-coder",
        "deepseek-coder",
        "codestral",
        "qwen3",
        "qwen2.5",
        "gemma4",
        "gemma3",
        "llama3.1",
        "mistral",
    ]

    for priority in priorities:

        for model in available_models:

            if (
                priority
                in model.casefold()
            ):
                return model

    return available_models[0]


def call_ollama(
    model,
    prompt,
):
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate constrained, safe, "
                    "regex-based Python extraction code. "
                    "Return Python code only. "
                    "When repair feedback is supplied, "
                    "fix every listed validation problem."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
        },
    }

    response = requests.post(
        OLLAMA_CHAT_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    content = (
        data
        .get(
            "message",
            {},
        )
        .get(
            "content",
            "",
        )
    )

    if not content.strip():
        raise RuntimeError(
            "Ollama boş cevap döndürdü."
        )

    return content


# =========================================================
# PROMPT
# =========================================================

def build_prompt(
    text,
    previous_code="",
    feedback="",
):
    fields_json = json.dumps(
        FIELDS,
        ensure_ascii=False,
        indent=4,
    )

    repair_section = ""

    if feedback:

        repair_section = f"""
============================================================
REPAIR MODE
============================================================

Önceki extractor çalıştırıldı ve VALIDATOR tarafından
başarısız bulundu.

Aşağıdaki feedback'i dikkatli oku.

VALIDATOR FEEDBACK:

{feedback}


ÖNCEKİ GENERATED CODE:

{previous_code}


ZORUNLU REPAIR KURALLARI:

1. Önceki kodu aynen tekrar etme.

2. Validator'ın söylediği TÜM hataları düzelt.

3. Bir regex source'taki değeri kaçırıyorsa regex'in
   gerçekten o formatı desteklediğinden emin ol.

4. Yüzde prefix veya suffix olabilir:

   %2,89
   % 2,89
   2,89%
   2,89 %

   Bunların hepsini destekle.

5. Kâr payı regex'inde:

   kâr payı / kar payı / kâr oranı / kar oranı

   bağlamı ZORUNLU olmalıdır.

   Bağlamı optional yapma.

6. Şu tarz geniş regex kullanma:

   [\\w\\s]*

   özellikle arada %, noktalama veya apostrof varsa
   eşleşmeyi bozabilir veya aşırı geniş eşleşebilir.

7. `masraf_bilgisi` için sadece:

   Tahsis ücreti

   gibi anahtar kelimeyi değil, mümkün olduğunca
   ilgili source cümlesinin TAMAMINI yakala.

8. `hedef_kitle` için Türkçe ekleri kaybetme.

   Source:
   "Yeni müşterilere"

   ise extractor:
   "Yeni müşteriler"

   döndürmemelidir.

   Exact source span'i döndür.

9. `finansman_tutari` için:

   "TL'ye kadar"
   "TL’ye kadar"
   "TL'ya kadar"
   "TL’ye dek"

   gibi üst limit eklerini source'ta varsa koru.

10. Somut source değerlerini hard-code ETME.

Kodun TAMAMINI yeniden üret.

Sadece Python kodu döndür.
"""

    return f"""
Sen Türkçe finansman metinleri için dinamik,
regex tabanlı Python extractor kodu üreten bir sistemsin.

Sana daha önce görülmemiş bir finansman metni verilecek.

GÖREVİN:

Veriyi doğrudan JSON olarak cevaplamak DEĞİL.

Bu metin ve benzer Türkçe finansman metinlerinden
bilgileri çıkarabilecek GENELLENEBİLİR Python regex
extractor kodu yazmaktır.


============================================================
FUNCTION
============================================================

Tam olarak şu fonksiyonu yaz:

def extract(text):

Başka fonksiyon tanımlama.


============================================================
OUTPUT
============================================================

Fonksiyon dict döndürmelidir.

Dict TAM OLARAK şu key'lere sahip olmalıdır:

{fields_json}


Bütün field değerleri LIST olmalıdır.


Başlangıç:

result = {{
    "kar_payi_orani": [],
    "finansman_orani": [],
    "finansman_tutari": [],
    "vade": [],
    "taksit_sayisi": [],
    "masraf_bilgisi": [],
    "hedef_kitle": [],
    "para_birimi": [],
    "kosullar": [],
}}


============================================================
PROVENANCE
============================================================

Çıkarılan HER değer source text'teki bir regex match
sonucundan gelmelidir.

Mümkün olduğunca:

match.group(0)

kullan.

Kaynak metindeki exact span'i koru.

Kaynakta olmayan kelime üretme.

Normalize ederek yeni bir değer üretme.


============================================================
NO HALLUCINATION
============================================================

Kaynakta açıkça olmayan alan:

[]

olarak bırakılmalıdır.

Tahmin yapma.


============================================================
NO HARD-CODING
============================================================

YANLIŞ:

result["vade"] = ["12 ay"]


YANLIŞ:

if "%2,89" in text:
    result["kar_payi_orani"].append(
        "%2,89"
    )


YANLIŞ:

if "150.000 TL" in text:
    result["finansman_tutari"].append(
        "150.000 TL"
    )


DOĞRU:

pattern = re.compile(
    r"...general regex...",
    re.IGNORECASE,
)

for match in pattern.finditer(text):

    value = match.group(0)

    if value not in result["..."]:
        result["..."].append(
            value
        )


============================================================
1. KAR PAYI ORANI
============================================================

Sadece kâr payı / kar payı bağlamındaki yüzdeyi çıkar.

Bağlam ZORUNLU olmalıdır.

Desteklenecek formatlar:

%2,89
% 2,89
%3.49
2,89%
3.49 %


Örneğin:

"aylık kâr payı oranı %2,89'dur"

içinden:

"%2,89"

çıkarılmalıdır.


Genel yüzde pattern ailesi şu mantığı desteklemelidir:

(?:%
   \\s*
   \\d+(?:[.,]\\d+)?
 |
   \\d+(?:[.,]\\d+)?
   \\s*%
)

Ancak bu yüzde pattern'i mutlaka kâr payı bağlamına
bağlı olmalıdır.


============================================================
2. FINANSMAN ORANI
============================================================

Yalnızca açıkça:

finansman oranı

bağlamındaki yüzdeyi çıkar.

Kâr payını finansman oranı olarak çıkarma.

Kaynakta finansman oranı yoksa:

[]


============================================================
3. FINANSMAN TUTARI
============================================================

Finansman miktarlarını ve limitlerini çıkar.

Örnek:

150.000 TL
150.000 TL'ye kadar
150.000 TL’ye kadar
50.000 - 100.000 TL
250 bin TL
1.000.000 TRY

Source'ta:

150.000 TL'ye kadar

varsa:

150.000 TL

şeklinde kısaltma yapma.

Tam span'i koru.


============================================================
4. VADE
============================================================

Örnek:

12 ay vadeli
36 aya kadar
24 aya kadar
2 yıl vadeli
2 - 6 ay

Source'ta "vadeli" varsa onu koru.


============================================================
5. TAKSIT SAYISI
============================================================

Sadece taksit bağlamındaki ifadeleri çıkar.

Örnek:

3 taksit
6 taksit
9 aya varan taksit

Vade bilgisini taksit sanma.


============================================================
6. MASRAF BILGISI
============================================================

Masraf / ücret / komisyon ile ilgili source cümlesini
mümkün olduğunca TAM yakala.

Örnek:

Tahsis ücreti alınmamaktadır.

çıktı:

Tahsis ücreti alınmamaktadır

olabilir.

Sadece:

Tahsis ücreti

şeklinde yarım bırakma.

Nokta işaretini dahil etmek zorunda değilsin.


============================================================
7. HEDEF KITLE
============================================================

Kaynakta açıkça belirtilmiş müşteri grubunu çıkar.

Örnek:

Yeni müşteriler
Yeni müşterilere
Bireysel müşteriler
Bireysel müşterilerimize
Emekliler
Öğrenciler
Kamu çalışanları

Türkçe ekleri source'ta olduğu şekilde koru.

Source:

Yeni müşterilere

ise exact olarak:

Yeni müşterilere

döndür.


============================================================
8. PARA BIRIMI
============================================================

Yalnızca source'ta geçen:

TL
TRY
USD
EUR

gibi para birimlerini çıkar.


============================================================
9. KOSULLAR
============================================================

Şart/kısıt belirten source ifadelerini çıkar.

Örnek sinyaller:

yararlanabilmek için
gerekmektedir
zorunludur
yalnızca
en az
en fazla
geçerlidir

Kaynakta açık koşul yoksa [].


============================================================
DUPLICATE
============================================================

Aynı değeri aynı listeye iki kere ekleme.


============================================================
ALLOWED
============================================================

Yalnızca:

import re

kullan.

İzinli:

re.compile
re.search
re.match
re.fullmatch
re.findall
re.finditer

for
if
list
dict
set
string operations


============================================================
FORBIDDEN
============================================================

Kullanma:

open
exec
eval
compile built-in
__import__
os
sys
subprocess
pathlib
requests
socket
urllib
shutil
network
file access
print
input
class
while
lambda
try/except
recursive call
extra function
globals
locals
getattr
setattr


============================================================
FINAL OUTPUT RULE
============================================================

Sadece Python kodunu döndür.

Markdown açıklaması yazma.

Kod dışında hiçbir metin yazma.


{repair_section}


============================================================
SOURCE TEXT
============================================================

--- SOURCE START ---

{text}

--- SOURCE END ---
""".strip()


# =========================================================
# MODEL OUTPUT -> PYTHON
# =========================================================

def extract_python_code(
    model_output,
):
    model_output = (
        model_output
        .strip()
    )

    fenced = re.search(
        r"```(?:python)?\s*(.*?)```",
        model_output,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if fenced:

        code = fenced.group(
            1
        ).strip()

    else:

        code = model_output

    starts = []

    import_index = code.find(
        "import re"
    )

    function_index = code.find(
        "def extract"
    )

    if import_index >= 0:
        starts.append(
            import_index
        )

    if function_index >= 0:
        starts.append(
            function_index
        )

    if starts:
        code = code[
            min(starts):
        ]

    return code.strip()


# =========================================================
# AST SECURITY
# =========================================================

def validate_generated_code(
    code,
):
    errors = []

    if not code.strip():
        return [
            "Generated code boş."
        ]

    if len(code) > 25000:
        return [
            "Generated code çok uzun."
        ]

    try:
        tree = ast.parse(
            code
        )

    except SyntaxError as error:
        return [
            (
                "Python syntax error: "
                f"{error}"
            )
        ]

    extract_functions = []

    # =====================================================
    # MODULE LEVEL
    # =====================================================

    for node in tree.body:

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if alias.name != "re":
                    errors.append(
                        (
                            "Sadece import re "
                            "kullanılabilir: "
                            f"{alias.name}"
                        )
                    )

                if alias.asname:
                    errors.append(
                        "import alias kullanılamaz."
                    )

        elif isinstance(
            node,
            ast.FunctionDef,
        ):

            if node.name != "extract":
                errors.append(
                    (
                        "extract dışında fonksiyon "
                        "tanımlanamaz: "
                        f"{node.name}"
                    )
                )

            else:
                extract_functions.append(
                    node
                )

        elif (
            isinstance(
                node,
                ast.Expr,
            )
            and
            isinstance(
                node.value,
                ast.Constant,
            )
            and
            isinstance(
                node.value.value,
                str,
            )
        ):
            pass

        else:

            errors.append(
                (
                    "Module seviyesinde sadece "
                    "import re ve extract(text) "
                    "olabilir."
                )
            )

    # =====================================================
    # FUNCTION SIGNATURE
    # =====================================================

    if len(extract_functions) != 1:

        errors.append(
            (
                "Tam olarak bir adet "
                "extract(text) fonksiyonu olmalı."
            )
        )

    else:

        function = extract_functions[0]

        args = [
            arg.arg
            for arg in function.args.args
        ]

        if args != [
            "text"
        ]:
            errors.append(
                (
                    "extract yalnızca text "
                    "parametresi almalıdır."
                )
            )

        if function.args.vararg:
            errors.append(
                "*args kullanılamaz."
            )

        if function.args.kwarg:
            errors.append(
                "**kwargs kullanılamaz."
            )

        if function.args.kwonlyargs:
            errors.append(
                "Keyword-only args kullanılamaz."
            )

        if function.decorator_list:
            errors.append(
                "Decorator kullanılamaz."
            )

    # =====================================================
    # AST WALK
    # =====================================================

    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            DISALLOWED_NODES,
        ):
            errors.append(
                (
                    "Yasak yapı: "
                    f"{type(node).__name__}"
                )
            )

        # -------------------------------------------------
        # IMPORT
        # -------------------------------------------------

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if alias.name != "re":
                    errors.append(
                        (
                            "Yasak import: "
                            f"{alias.name}"
                        )
                    )

        # -------------------------------------------------
        # NAME
        # -------------------------------------------------

        if isinstance(
            node,
            ast.Name,
        ):

            if node.id in DANGEROUS_NAMES:
                errors.append(
                    (
                        "Yasak isim: "
                        f"{node.id}"
                    )
                )

        # -------------------------------------------------
        # ATTRIBUTE
        # -------------------------------------------------

        if isinstance(
            node,
            ast.Attribute,
        ):

            if node.attr.startswith(
                "_"
            ):
                errors.append(
                    (
                        "Private/dunder attribute "
                        "yasak: "
                        f".{node.attr}"
                    )
                )

            if (
                isinstance(
                    node.value,
                    ast.Name,
                )
                and
                node.value.id == "re"
            ):

                if (
                    node.attr
                    not in SAFE_RE_ATTRIBUTES
                ):
                    errors.append(
                        (
                            "İzin verilmeyen re "
                            "attribute: "
                            f"re.{node.attr}"
                        )
                    )

        # -------------------------------------------------
        # CALL
        # -------------------------------------------------

        if isinstance(
            node,
            ast.Call,
        ):

            if isinstance(
                node.func,
                ast.Name,
            ):

                name = node.func.id

                if (
                    name
                    not in SAFE_BUILTIN_CALLS
                ):
                    errors.append(
                        (
                            "İzin verilmeyen "
                            "function call: "
                            f"{name}"
                        )
                    )

            elif isinstance(
                node.func,
                ast.Attribute,
            ):

                method = node.func.attr

                if (
                    isinstance(
                        node.func.value,
                        ast.Name,
                    )
                    and
                    node.func.value.id == "re"
                ):

                    if (
                        method
                        not in SAFE_RE_CALLS
                    ):
                        errors.append(
                            (
                                "İzin verilmeyen "
                                "regex call: "
                                f"re.{method}"
                            )
                        )

                elif (
                    method
                    not in SAFE_METHOD_CALLS
                ):

                    errors.append(
                        (
                            "İzin verilmeyen "
                            "method call: "
                            f".{method}"
                        )
                    )

            else:

                errors.append(
                    (
                        "Dinamik function call "
                        "kullanılamaz."
                    )
                )

    if "re." not in code:
        errors.append(
            "Kod regex kullanmıyor."
        )

    if re.search(
        r"\bprint\s*\(",
        code,
    ):
        errors.append(
            "print kullanılamaz."
        )

    return list(
        dict.fromkeys(
            errors
        )
    )


# =========================================================
# CODE RUNNER
# =========================================================

def run_generated_code(
    code,
    text,
):
    wrapper = f"""
import json
import sys

try:
    import resource

    try:
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (3, 3),
        )
    except Exception:
        pass

    try:
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (
                1024 * 1024,
                1024 * 1024,
            ),
        )
    except Exception:
        pass

except Exception:
    pass


{code}


payload = json.loads(
    sys.stdin.read()
)

result = extract(
    payload["text"]
)

sys.stdout.write(
    json.dumps(
        result,
        ensure_ascii=False,
    )
)
""".strip()

    with tempfile.TemporaryDirectory() as temp_dir:

        script_path = (
            Path(temp_dir)
            / "runner.py"
        )

        script_path.write_text(
            wrapper,
            encoding="utf-8",
        )

        try:

            process = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(script_path),
                ],
                input=json.dumps(
                    {
                        "text": text,
                    },
                    ensure_ascii=False,
                ),
                capture_output=True,
                text=True,
                timeout=CODE_TIMEOUT,
                env={
                    "PATH": os.environ.get(
                        "PATH",
                        "",
                    ),
                    "PYTHONNOUSERSITE": "1",
                },
            )

        except subprocess.TimeoutExpired:

            raise RuntimeError(
                (
                    "Generated extractor "
                    f"{CODE_TIMEOUT} saniyede "
                    "timeout oldu."
                )
            )

    if process.returncode != 0:

        raise RuntimeError(
            (
                "Generated extractor runtime error:\n"
                f"{process.stderr.strip()}"
            )
        )

    stdout = (
        process.stdout
        .strip()
    )

    if not stdout:

        raise RuntimeError(
            "Generated extractor boş çıktı."
        )

    try:

        result = json.loads(
            stdout
        )

    except json.JSONDecodeError:

        raise RuntimeError(
            (
                "Generated extractor geçerli "
                "JSON üretmedi:\n"
                f"{stdout}"
            )
        )

    return result


# =========================================================
# EXPECTED EVIDENCE DETECTOR
# =========================================================

def regex_spans(
    pattern,
    text,
    flags=re.IGNORECASE,
):
    values = []

    for match in re.finditer(
        pattern,
        text,
        flags,
    ):

        value = clean_text(
            match.group(0)
        )

        if value:
            values.append(
                value
            )

    return unique_strings(
        values
    )


def detect_expected_evidence(
    source_text,
):
    expected = {
        "kar_payi_orani": [],
        "finansman_orani": [],
        "finansman_tutari": [],
        "vade": [],
        "taksit_sayisi": [],
        "masraf_bilgisi": [],
        "hedef_kitle": [],
        "para_birimi": [],
    }

    text = source_text

    # =====================================================
    # KAR PAYI
    # =====================================================

    kar_patterns = [
        (
            r"(?:aylık\s+)?"
            r"(?:kâr|kar)\s+"
            r"(?:payı|payi)"
            r"(?:\s+(?:oranı|orani))?"
            r"\s*"
            r"(?:[:=]\s*)?"
            r"%\s*\d+(?:[.,]\d+)?"
        ),
        (
            r"(?:aylık\s+)?"
            r"(?:kâr|kar)\s+"
            r"(?:oranı|orani)"
            r"\s*"
            r"(?:[:=]\s*)?"
            r"%\s*\d+(?:[.,]\d+)?"
        ),
        (
            r"(?:aylık\s+)?"
            r"(?:kâr|kar)\s+"
            r"(?:payı|payi)"
            r"(?:\s+(?:oranı|orani))?"
            r"\s*"
            r"(?:[:=]\s*)?"
            r"\d+(?:[.,]\d+)?\s*%"
        ),
    ]

    for pattern in kar_patterns:

        for match in regex_spans(
            pattern,
            text,
        ):

            percentage = re.search(
                (
                    r"%\s*\d+(?:[.,]\d+)?"
                    r"|"
                    r"\d+(?:[.,]\d+)?\s*%"
                ),
                match,
                re.IGNORECASE,
            )

            if percentage:

                expected[
                    "kar_payi_orani"
                ].append(
                    clean_text(
                        percentage.group(0)
                    )
                )

    expected[
        "kar_payi_orani"
    ] = unique_strings(
        expected[
            "kar_payi_orani"
        ]
    )

    # =====================================================
    # FINANSMAN ORANI
    # =====================================================

    finance_ratio_patterns = [
        (
            r"finansman\s+"
            r"(?:oranı|orani)"
            r"\s*"
            r"(?:[:=]\s*)?"
            r"%\s*\d+(?:[.,]\d+)?"
        ),
        (
            r"finansman\s+"
            r"(?:oranı|orani)"
            r"\s*"
            r"(?:[:=]\s*)?"
            r"\d+(?:[.,]\d+)?\s*%"
        ),
    ]

    for pattern in finance_ratio_patterns:

        for match in regex_spans(
            pattern,
            text,
        ):

            percentage = re.search(
                (
                    r"%\s*\d+(?:[.,]\d+)?"
                    r"|"
                    r"\d+(?:[.,]\d+)?\s*%"
                ),
                match,
                re.IGNORECASE,
            )

            if percentage:

                expected[
                    "finansman_orani"
                ].append(
                    clean_text(
                        percentage.group(0)
                    )
                )

    expected[
        "finansman_orani"
    ] = unique_strings(
        expected[
            "finansman_orani"
        ]
    )

    # =====================================================
    # FINANSMAN TUTARI
    # =====================================================

    money_pattern = re.compile(
        (
            r"\b"
            r"\d{1,3}"
            r"(?:[.\s]\d{3})*"
            r"(?:,\d+)?"
            r"(?:"
            r"\s*[-–]\s*"
            r"\d{1,3}"
            r"(?:[.\s]\d{3})*"
            r"(?:,\d+)?"
            r")?"
            r"\s*"
            r"(?:TL|TRY|USD|EUR)"
            r"(?:"
            r"['’]?"
            r"(?:ye|ya)"
            r")?"
            r"(?:\s+kadar)?"
        ),
        re.IGNORECASE,
    )

    for match in money_pattern.finditer(
        text
    ):

        start = max(
            0,
            match.start() - 90,
        )

        end = min(
            len(text),
            match.end() + 90,
        )

        context = (
            text[start:end]
            .casefold()
        )

        if "finansman" in context:

            expected[
                "finansman_tutari"
            ].append(
                clean_text(
                    match.group(0)
                )
            )

    expected[
        "finansman_tutari"
    ] = unique_strings(
        expected[
            "finansman_tutari"
        ]
    )

    # =====================================================
    # VADE
    # =====================================================

    vade_patterns = [
        r"\b\d+\s+(?:ay|yıl)\s+vadeli\b",
        r"\b\d+\s+(?:aya|yıla)\s+kadar\b",
        (
            r"\b\d+\s*[-–]\s*\d+\s+"
            r"(?:ay|yıl)\b"
        ),
    ]

    for pattern in vade_patterns:

        expected[
            "vade"
        ].extend(
            regex_spans(
                pattern,
                text,
            )
        )

    expected[
        "vade"
    ] = unique_strings(
        expected[
            "vade"
        ]
    )

    # =====================================================
    # TAKSIT
    # =====================================================

    taksit_patterns = [
        r"\b\d+\s+taksit\b",
        r"\b\d+\s+aya\s+varan\s+taksit\b",
    ]

    for pattern in taksit_patterns:

        expected[
            "taksit_sayisi"
        ].extend(
            regex_spans(
                pattern,
                text,
            )
        )

    expected[
        "taksit_sayisi"
    ] = unique_strings(
        expected[
            "taksit_sayisi"
        ]
    )

    # =====================================================
    # MASRAF
    # =====================================================

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    fee_keywords = (
        "tahsis ücreti",
        "tahsis ucreti",
        "dosya masrafı",
        "dosya masrafi",
        "komisyon",
        "masraf",
        "ücret",
        "ucret",
    )

    for sentence in sentences:

        cleaned = clean_text(
            sentence
        )

        normalized = (
            cleaned
            .casefold()
        )

        if any(
            keyword in normalized
            for keyword in fee_keywords
        ):

            expected[
                "masraf_bilgisi"
            ].append(
                cleaned.rstrip(
                    "."
                )
            )

    expected[
        "masraf_bilgisi"
    ] = unique_strings(
        expected[
            "masraf_bilgisi"
        ]
    )

    # =====================================================
    # HEDEF KITLE
    # =====================================================

    target_patterns = [
        r"\byeni\s+müşterilere\b",
        r"\byeni\s+müşterilerimize\b",
        r"\byeni\s+müşteriler\b",

        r"\bbireysel\s+müşterilere\b",
        r"\bbireysel\s+müşterilerimize\b",
        r"\bbireysel\s+müşteriler\b",

        r"\bemeklilere\b",
        r"\bemekliler\b",

        r"\böğrencilere\b",
        r"\böğrenciler\b",

        r"\bkamu\s+çalışanlarına\b",
        r"\bkamu\s+çalışanları\b",
    ]

    for pattern in target_patterns:

        expected[
            "hedef_kitle"
        ].extend(
            regex_spans(
                pattern,
                text,
            )
        )

    # En uzun exact formu tercih et.
    expected[
        "hedef_kitle"
    ] = sorted(
        unique_strings(
            expected[
                "hedef_kitle"
            ]
        ),
        key=len,
        reverse=True,
    )

    # Eğer uzun form kısa formu içeriyorsa
    # kısa olanı çıkar.
    filtered_targets = []

    for candidate in expected[
        "hedef_kitle"
    ]:

        candidate_n = (
            candidate
            .casefold()
        )

        redundant = False

        for existing in filtered_targets:

            existing_n = (
                existing
                .casefold()
            )

            if (
                candidate_n
                in existing_n
            ):
                redundant = True
                break

        if not redundant:
            filtered_targets.append(
                candidate
            )

    expected[
        "hedef_kitle"
    ] = filtered_targets

    # =====================================================
    # CURRENCY
    # =====================================================

    expected[
        "para_birimi"
    ] = regex_spans(
        r"\b(?:TL|TRY|USD|EUR)\b",
        text,
    )

    return expected


# =========================================================
# SEMANTIC HELPERS
# =========================================================

def semantic_values_equal(
    left,
    right,
):
    return (
        normalize_semantic(
            left
        )
        ==
        normalize_semantic(
            right
        )
    )


def expected_value_found(
    extracted_values,
    expected_value,
):
    for extracted in extracted_values:

        if not isinstance(
            extracted,
            str,
        ):
            continue

        if semantic_values_equal(
            extracted,
            expected_value,
        ):
            return True

    return False


def source_context_for_value(
    source_text,
    value,
    window=80,
):
    source_cf = (
        source_text
        .casefold()
    )

    value_cf = (
        clean_text(
            value
        )
        .casefold()
    )

    index = source_cf.find(
        value_cf
    )

    if index < 0:
        return ""

    start = max(
        0,
        index - window,
    )

    end = min(
        len(source_text),
        index
        + len(value)
        + window,
    )

    return source_text[
        start:end
    ]


# =========================================================
# SEMANTIC VALIDATOR V3
# =========================================================

def validate_semantics_v3(
    result,
    source_text,
):
    errors = []

    expected = detect_expected_evidence(
        source_text
    )

    # =====================================================
    # STRICT RECALL
    # =====================================================

    strict_fields = [
        "kar_payi_orani",
        "finansman_orani",
        "finansman_tutari",
        "vade",
        "taksit_sayisi",
        "masraf_bilgisi",
        "hedef_kitle",
        "para_birimi",
    ]

    for field in strict_fields:

        expected_values = expected.get(
            field,
            [],
        )

        extracted_values = result.get(
            field,
            [],
        )

        if not isinstance(
            extracted_values,
            list,
        ):
            continue

        for expected_value in expected_values:

            if not expected_value_found(
                extracted_values,
                expected_value,
            ):

                errors.append(
                    (
                        f"{field}: source içinde "
                        f"{expected_value!r} açıkça "
                        "bulunuyor fakat extractor "
                        "bu exact span'i çıkarmadı."
                    )
                )

    # =====================================================
    # FALSE POSITIVE
    # =====================================================

    strict_empty_fields = [
        "kar_payi_orani",
        "finansman_orani",
        "taksit_sayisi",
    ]

    for field in strict_empty_fields:

        expected_values = expected.get(
            field,
            [],
        )

        extracted_values = result.get(
            field,
            [],
        )

        if (
            not expected_values
            and
            isinstance(
                extracted_values,
                list,
            )
            and
            extracted_values
        ):

            errors.append(
                (
                    f"{field}: source'ta bu alan "
                    "için yüksek güvenli evidence "
                    "yokken değer üretildi: "
                    f"{extracted_values}"
                )
            )

    # =====================================================
    # KAR PAYI SANITY
    # =====================================================

    kar_values = result.get(
        "kar_payi_orani",
        [],
    )

    if isinstance(
        kar_values,
        list,
    ):

        for value in kar_values:

            if not isinstance(
                value,
                str,
            ):
                continue

            if "%" not in value:

                errors.append(
                    (
                        "kar_payi_orani: "
                        f"{value!r} yüzde "
                        "işareti içermiyor."
                    )
                )

                continue

            context = (
                source_context_for_value(
                    source_text,
                    value,
                )
                .casefold()
            )

            if (
                "kâr pay"
                not in context
                and
                "kar pay"
                not in context
                and
                "kâr oran"
                not in context
                and
                "kar oran"
                not in context
            ):

                errors.append(
                    (
                        "kar_payi_orani: "
                        f"{value!r} kâr payı "
                        "bağlamında değil."
                    )
                )

    # =====================================================
    # FINANSMAN ORANI SANITY
    # =====================================================

    ratio_values = result.get(
        "finansman_orani",
        [],
    )

    if isinstance(
        ratio_values,
        list,
    ):

        for value in ratio_values:

            if not isinstance(
                value,
                str,
            ):
                continue

            if "%" not in value:

                errors.append(
                    (
                        "finansman_orani: "
                        f"{value!r} yüzde "
                        "işareti içermiyor."
                    )
                )

                continue

            context = (
                source_context_for_value(
                    source_text,
                    value,
                )
                .casefold()
            )

            if (
                "finansman oran"
                not in context
            ):

                errors.append(
                    (
                        "finansman_orani: "
                        f"{value!r} finansman oranı "
                        "bağlamında değil."
                    )
                )

    # =====================================================
    # TAKSIT SANITY
    # =====================================================

    installment_values = result.get(
        "taksit_sayisi",
        [],
    )

    if isinstance(
        installment_values,
        list,
    ):

        for value in installment_values:

            if not isinstance(
                value,
                str,
            ):
                continue

            context = (
                source_context_for_value(
                    source_text,
                    value,
                )
                .casefold()
            )

            if "taksit" not in context:

                errors.append(
                    (
                        "taksit_sayisi: "
                        f"{value!r} taksit "
                        "bağlamında değil."
                    )
                )

    return (
        errors,
        expected,
    )


# =========================================================
# OUTPUT VALIDATION
# =========================================================

def validate_output(
    result,
    source_text,
):
    errors = []

    if not isinstance(
        result,
        dict,
    ):

        return (
            [
                (
                    "Extractor sonucu dict değil: "
                    f"{type(result).__name__}"
                )
            ],
            {},
        )

    expected_keys = set(
        FIELDS
    )

    actual_keys = set(
        result.keys()
    )

    missing = (
        expected_keys
        - actual_keys
    )

    extra = (
        actual_keys
        - expected_keys
    )

    if missing:
        errors.append(
            (
                "Eksik field: "
                f"{sorted(missing)}"
            )
        )

    if extra:
        errors.append(
            (
                "Fazladan field: "
                f"{sorted(extra)}"
            )
        )

    # =====================================================
    # PROVENANCE
    # =====================================================

    source_normalized = (
        normalize_for_compare(
            source_text
        )
    )

    for field in FIELDS:

        values = result.get(
            field
        )

        if not isinstance(
            values,
            list,
        ):

            errors.append(
                (
                    f"{field} list değil. "
                    f"Actual: {type(values).__name__}"
                )
            )

            continue

        seen = set()

        for value in values:

            if not isinstance(
                value,
                str,
            ):

                errors.append(
                    (
                        f"{field}: string olmayan "
                        f"değer: {value!r}"
                    )
                )

                continue

            cleaned = clean_text(
                value
            )

            if not cleaned:

                errors.append(
                    (
                        f"{field}: boş string "
                        "bulundu."
                    )
                )

                continue

            normalized = (
                normalize_for_compare(
                    cleaned
                )
            )

            if (
                normalized
                not in source_normalized
            ):

                errors.append(
                    (
                        f"{field}: {cleaned!r} "
                        "source içinde exact span "
                        "olarak bulunmuyor."
                    )
                )

            if normalized in seen:

                errors.append(
                    (
                        f"{field}: duplicate "
                        f"{cleaned!r}"
                    )
                )

            seen.add(
                normalized
            )

    # =====================================================
    # SEMANTIC
    # =====================================================

    semantic_errors, expected = (
        validate_semantics_v3(
            result=result,
            source_text=source_text,
        )
    )

    errors.extend(
        semantic_errors
    )

    return (
        list(
            dict.fromkeys(
                errors
            )
        ),
        expected,
    )


# =========================================================
# SMART REPAIR HINT GENERATOR
# =========================================================

def build_repair_hints(
    errors,
    expected,
    result,
):
    hints = []

    # =====================================================
    # KAR PAYI
    # =====================================================

    if expected.get(
        "kar_payi_orani"
    ):

        extracted = result.get(
            "kar_payi_orani",
            [],
        )

        missing = any(
            not expected_value_found(
                extracted,
                value,
            )
            for value in expected[
                "kar_payi_orani"
            ]
        )

        if missing:

            hints.append(
                (
                    "KAR PAYI REPAIR HINT:\n"
                    "- Source yüzdeyi prefix formatında "
                    "kullanabilir: %2,89.\n"
                    "- Regex hem `%2,89` hem `2,89%` "
                    "formatını desteklemelidir.\n"
                    "- `%` işaretini sayının sadece "
                    "sonunda arama.\n"
                    "- Kâr payı bağlamını zorunlu tut.\n"
                    "- Bağlam ile yüzde arasındaki "
                    "`oranı`, `oran`, `aylık` gibi "
                    "kelimeleri destekle.\n"
                    "- `\\w` yüzde işaretini kapsamaz; "
                    "bu nedenle `\\w\\s*` ile yüzdeye "
                    "ulaşmaya güvenme.\n"
                    "- Extract edilen value yalnızca "
                    "yüzde span'i olabilir."
                )
            )

    # =====================================================
    # FINANCE RATIO
    # =====================================================

    if (
        not expected.get(
            "finansman_orani"
        )
        and
        result.get(
            "finansman_orani"
        )
    ):

        hints.append(
            (
                "FINANSMAN ORANI REPAIR HINT:\n"
                "- Source'ta açık `finansman oranı` "
                "ifadesi yok.\n"
                "- Genel sayıları/yüzdeleri bu alana "
                "ekleme.\n"
                "- `finansman oranı` bağlamını "
                "zorunlu hale getir."
            )
        )

    # =====================================================
    # AMOUNT
    # =====================================================

    if expected.get(
        "finansman_tutari"
    ):

        extracted = result.get(
            "finansman_tutari",
            [],
        )

        missing = any(
            not expected_value_found(
                extracted,
                value,
            )
            for value in expected[
                "finansman_tutari"
            ]
        )

        if missing:

            hints.append(
                (
                    "FINANSMAN TUTARI REPAIR HINT:\n"
                    "- Para biriminden sonraki "
                    "`'ye kadar`, `’ye kadar`, "
                    "`'ya kadar`, `’ya kadar` "
                    "eklerini regex'in içine dahil et.\n"
                    "- Sadece parasal gövdeyi değil "
                    "limit anlamını taşıyan tam source "
                    "span'i döndür."
                )
            )

    # =====================================================
    # VADE
    # =====================================================

    if expected.get(
        "vade"
    ):

        extracted = result.get(
            "vade",
            [],
        )

        missing = any(
            not expected_value_found(
                extracted,
                value,
            )
            for value in expected[
                "vade"
            ]
        )

        if missing:

            hints.append(
                (
                    "VADE REPAIR HINT:\n"
                    "- `12 ay vadeli` gibi source "
                    "ifadelerinde `vadeli` kelimesini "
                    "kaybetme.\n"
                    "- `aya kadar`, `yıla kadar`, "
                    "`x - y ay` biçimlerini destekle."
                )
            )

    # =====================================================
    # FEE
    # =====================================================

    if expected.get(
        "masraf_bilgisi"
    ):

        extracted = result.get(
            "masraf_bilgisi",
            [],
        )

        missing = any(
            not expected_value_found(
                extracted,
                value,
            )
            for value in expected[
                "masraf_bilgisi"
            ]
        )

        if missing:

            hints.append(
                (
                    "MASRAF REPAIR HINT:\n"
                    "- Sadece `Tahsis ücreti` gibi "
                    "anahtar kelimeyi yakalama.\n"
                    "- Masraf anahtar kelimesinden "
                    "cümle sonuna kadar ilgili "
                    "source span'i yakala.\n"
                    "- Örneğin `alınmamaktadır`, "
                    "`alınır`, `%... oranındadır`, "
                    "`yoktur` gibi devam kısımlarını "
                    "koru.\n"
                    "- Nokta karakterini çıktı içine "
                    "almak zorunda değilsin."
                )
            )

    # =====================================================
    # TARGET
    # =====================================================

    if expected.get(
        "hedef_kitle"
    ):

        extracted = result.get(
            "hedef_kitle",
            [],
        )

        missing = any(
            not expected_value_found(
                extracted,
                value,
            )
            for value in expected[
                "hedef_kitle"
            ]
        )

        if missing:

            hints.append(
                (
                    "HEDEF KITLE REPAIR HINT:\n"
                    "- Türkçe çekim eklerini source'ta "
                    "olduğu gibi koru.\n"
                    "- `Yeni müşterilere` source'ta "
                    "geçiyorsa sadece "
                    "`Yeni müşteriler` döndürme.\n"
                    "- Pattern hedef grup gövdesinden "
                    "sonraki `e`, `a`, `imize`, "
                    "`ımıza` gibi uygun ekleri de "
                    "match edebilmelidir.\n"
                    "- Exact source span'i döndür."
                )
            )

    # =====================================================
    # TAKSIT
    # =====================================================

    if (
        not expected.get(
            "taksit_sayisi"
        )
        and
        result.get(
            "taksit_sayisi"
        )
    ):

        hints.append(
            (
                "TAKSIT REPAIR HINT:\n"
                "- Source'ta açık `taksit` "
                "bağlamı yoksa taksit üretme.\n"
                "- Ay/vade ifadelerini taksit "
                "sayısı sanma."
            )
        )

    # =====================================================
    # FALLBACK
    # =====================================================

    if not hints:

        hints.append(
            (
                "GENEL REPAIR HINT:\n"
                "- Validator hatalarını tek tek incele.\n"
                "- Source exact span'lerini koru.\n"
                "- Regex'leri aşırı genel yapma.\n"
                "- Somut source değerlerini "
                "hard-code etme."
            )
        )

    return "\n\n".join(
        hints
    )


# =========================================================
# SAVE
# =========================================================

def save_successful_run(
    model,
    source_text,
    generated_code,
    result,
    attempt,
):
    output_dir = (
        ROOT
        / "data"
        / "generated"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    code_file = (
        output_dir
        / f"dynamic_regex_v3_{timestamp}.py"
    )

    result_file = (
        output_dir
        / f"dynamic_regex_v3_{timestamp}.json"
    )

    code_file.write_text(
        generated_code,
        encoding="utf-8",
    )

    payload = {
        "version": "V3",
        "model": model,
        "successful_attempt": attempt,
        "source_text": source_text,
        "result": result,
    }

    result_file.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return (
        code_file,
        result_file,
    )


# =========================================================
# INPUT
# =========================================================

def read_input_text(
    args,
):
    if args.text:

        text = clean_text(
            args.text
        )

        if not text:
            raise ValueError(
                "--text boş."
            )

        return text

    if args.input:

        path = Path(
            args.input
        )

        if not path.exists():

            raise FileNotFoundError(
                (
                    "Input dosyası bulunamadı: "
                    f"{path}"
                )
            )

        text = clean_text(
            path.read_text(
                encoding="utf-8",
            )
        )

        if not text:

            raise ValueError(
                "Input dosyası boş."
            )

        return text

    raise ValueError(
        (
            "Ya --text ya da "
            "--input verilmelidir."
        )
    )


# =========================================================
# MAIN
# =========================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Ollama dynamic regex "
            "extractor V3"
        )
    )

    parser.add_argument(
        "--text",
        type=str,
        default="",
    )

    parser.add_argument(
        "--input",
        type=str,
        default="",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="",
    )

    args = parser.parse_args()

    print()

    print(
        "=" * 120
    )

    print(
        "DYNAMIC REGEX EXTRACTOR V3"
    )

    print(
        "=" * 120
    )

    # =====================================================
    # INPUT
    # =====================================================

    source_text = read_input_text(
        args
    )

    print(
        "Input karakter:",
        len(
            source_text
        ),
    )

    print()

    print(
        "SOURCE TEXT"
    )

    print(
        "-" * 120
    )

    print(
        source_text
    )

    print(
        "-" * 120
    )

    # =====================================================
    # EXPECTED EVIDENCE
    # =====================================================

    initial_expected = (
        detect_expected_evidence(
            source_text
        )
    )

    print()

    print(
        "SEMANTIC VALIDATOR EXPECTED EVIDENCE"
    )

    print(
        "-" * 120
    )

    print(
        json.dumps(
            initial_expected,
            ensure_ascii=False,
            indent=4,
        )
    )

    print(
        "-" * 120
    )

    # =====================================================
    # MODEL
    # =====================================================

    available_models = (
        get_available_models()
    )

    print()

    print(
        "OLLAMA MODELLERİ"
    )

    print(
        "-" * 120
    )

    for model_name in available_models:

        print(
            "-",
            model_name,
        )

    model = choose_model(
        available_models=available_models,
        requested_model=(
            args.model
            if args.model
            else None
        ),
    )

    print()

    print(
        "Seçilen model:",
        model,
    )

    # =====================================================
    # LOOP
    # =====================================================

    previous_code = ""
    feedback = ""

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        print()

        print(
            "=" * 120
        )

        print(
            (
                f"ATTEMPT "
                f"{attempt}/{MAX_RETRIES}"
            )
        )

        print(
            "=" * 120
        )

        prompt = build_prompt(
            text=source_text,
            previous_code=previous_code,
            feedback=feedback,
        )

        print(
            "LLM regex extractor kodu üretiyor..."
        )

        # =================================================
        # LLM
        # =================================================

        try:

            model_output = call_ollama(
                model=model,
                prompt=prompt,
            )

        except Exception as error:

            print()

            print(
                "OLLAMA CALL: FAIL ❌"
            )

            print(
                error
            )

            feedback = (
                "OLLAMA CALL FAILED:\n"
                + str(error)
            )

            continue

        generated_code = (
            extract_python_code(
                model_output
            )
        )

        print()

        print(
            "GENERATED CODE"
        )

        print(
            "-" * 120
        )

        print(
            generated_code
        )

        print(
            "-" * 120
        )

        # =================================================
        # SECURITY
        # =================================================

        security_errors = (
            validate_generated_code(
                generated_code
            )
        )

        if security_errors:

            print()

            print(
                "CODE SECURITY: FAIL ❌"
            )

            for error in security_errors:

                print(
                    "-",
                    error,
                )

            previous_code = (
                generated_code
            )

            feedback = (
                "CODE SECURITY FAILED:\n"
                + "\n".join(
                    security_errors
                )
            )

            continue

        print()

        print(
            "CODE SECURITY: PASS ✅"
        )

        # =================================================
        # RUN
        # =================================================

        try:

            result = run_generated_code(
                code=generated_code,
                text=source_text,
            )

        except Exception as error:

            print()

            print(
                "CODE RUNNER: FAIL ❌"
            )

            print(
                error
            )

            previous_code = (
                generated_code
            )

            feedback = (
                "CODE RUNTIME FAILED:\n"
                + str(error)
            )

            continue

        print(
            "CODE RUNNER: PASS ✅"
        )

        # =================================================
        # RESULT
        # =================================================

        print()

        print(
            "RAW EXTRACTED RESULT"
        )

        print(
            "-" * 120
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=4,
            )
        )

        print(
            "-" * 120
        )

        # =================================================
        # VALIDATE
        # =================================================

        output_errors, expected = (
            validate_output(
                result=result,
                source_text=source_text,
            )
        )

        if output_errors:

            print()

            print(
                "OUTPUT VALIDATION: FAIL ❌"
            )

            for error in output_errors:

                print(
                    "-",
                    error,
                )

            repair_hints = (
                build_repair_hints(
                    errors=output_errors,
                    expected=expected,
                    result=result,
                )
            )

            print()

            print(
                "SMART REPAIR HINTS"
            )

            print(
                "-" * 120
            )

            print(
                repair_hints
            )

            print(
                "-" * 120
            )

            previous_code = (
                generated_code
            )

            feedback = (
                "VALIDATION ERRORS:\n"
                + "\n".join(
                    output_errors
                )
                + "\n\n"
                + "EXPECTED EVIDENCE:\n"
                + json.dumps(
                    expected,
                    ensure_ascii=False,
                    indent=4,
                )
                + "\n\n"
                + "SMART REPAIR HINTS:\n"
                + repair_hints
                + "\n\n"
                + "ACTUAL RESULT:\n"
                + json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=4,
                )
            )

            if attempt < MAX_RETRIES:

                print()

                print(
                    (
                        "Validator + repair hints "
                        "LLM'e gönderiliyor 🔁"
                    )
                )

            continue

        # =================================================
        # SUCCESS
        # =================================================

        print()

        print(
            "OUTPUT VALIDATION: PASS ✅"
        )

        code_file, result_file = (
            save_successful_run(
                model=model,
                source_text=source_text,
                generated_code=generated_code,
                result=result,
                attempt=attempt,
            )
        )

        print()

        print(
            "=" * 120
        )

        print(
            "FINAL RESULT"
        )

        print(
            "=" * 120
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=4,
            )
        )

        print()

        print(
            (
                "SONUÇ: DYNAMIC REGEX "
                "EXTRACTION V3 BAŞARILI ✅"
            )
        )

        print(
            (
                "Başarılı attempt: "
                f"{attempt}/{MAX_RETRIES} ✅"
            )
        )

        print(
            "Generated code:",
            code_file,
        )

        print(
            "Result:",
            result_file,
        )

        print(
            "=" * 120
        )

        return

    # =====================================================
    # FAILURE
    # =====================================================

    print()

    print(
        "=" * 120
    )

    print(
        (
            "SONUÇ: DYNAMIC REGEX "
            "EXTRACTION V3 BAŞARISIZ ❌"
        )
    )

    print(
        (
            f"{MAX_RETRIES} attempt sonunda "
            "validator'dan geçen extractor "
            "üretilemedi."
        )
    )

    print(
        "=" * 120
    )

    sys.exit(
        1
    )


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nKullanıcı tarafından durduruldu."
        )

        sys.exit(
            130
        )

    except Exception as error:

        print()

        print(
            "DYNAMIC EXTRACTOR ERROR ❌"
        )

        print(
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )

        sys.exit(
            1
        )