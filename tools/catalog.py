"""おうちストックのカタログ（よく買う食材・日用品）の定義と、画像の生成。
使い方:
  python tools/catalog.py js            -> catalog.js を書き出す
  python tools/catalog.py gen [id ...]  -> ローカルのComfyUI(Z-Image Turbo)で img/<id>.webp を作る（既存はスキップ。id指定で作り直し）
"""
import io
import json
import random
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMFY = "http://127.0.0.1:8188"

# (id, 商品名, カテゴリ, 単位, 英語の説明)
CATALOG = [
    # 野菜
    ("cabbage", "キャベツ", "veg", "玉", "a whole round green cabbage"),
    ("lettuce", "レタス", "veg", "玉", "a whole head of fresh green iceberg lettuce"),
    ("onion", "玉ねぎ", "veg", "個", "two golden brown onions"),
    ("carrot", "にんじん", "veg", "本", "three orange carrots with short green leaves"),
    ("potato", "じゃがいも", "veg", "個", "three round brown potatoes"),
    ("tomato", "トマト", "veg", "個", "two shiny red tomatoes with green stems"),
    ("cucumber", "きゅうり", "veg", "本", "two long green Japanese cucumbers"),
    ("eggplant", "なす", "veg", "本", "two glossy dark purple Japanese eggplants"),
    ("greenpepper", "ピーマン", "veg", "個", "three shiny green bell peppers"),
    ("broccoli", "ブロッコリー", "veg", "株", "a fresh green broccoli head"),
    ("spinach", "ほうれん草", "veg", "束", "a bunch of fresh spinach with pink roots"),
    ("komatsuna", "小松菜", "veg", "束", "a bunch of Japanese komatsuna mustard greens"),
    ("moyashi", "もやし", "veg", "袋", "a small clear plastic bag of white bean sprouts"),
    ("daikon", "大根", "veg", "本", "a long white daikon radish with green leaves"),
    ("negi", "長ねぎ", "veg", "本", "two long Japanese green onions (negi), white bottom and green top"),
    ("hakusai", "白菜", "veg", "個", "a whole Napa cabbage (hakusai)"),
    ("kabocha", "かぼちゃ", "veg", "個", "a dark green Japanese kabocha squash"),
    ("shimeji", "しめじ", "veg", "パック", "a cluster of brown shimeji mushrooms"),
    ("enoki", "えのき", "veg", "袋", "a bundle of white enoki mushrooms"),
    ("sweetpotato", "さつまいも", "veg", "本", "two purple-red Japanese sweet potatoes"),
    # 果物
    ("banana", "バナナ", "fruit", "房", "a bunch of yellow bananas"),
    ("apple", "りんご", "fruit", "個", "two shiny red apples"),
    ("mikan", "みかん", "fruit", "個", "three small orange mandarin oranges with a leaf"),
    ("strawberry", "いちご", "fruit", "パック", "a small pile of red strawberries"),
    # 肉
    ("chicken_breast", "鶏むね肉", "meat", "パック", "raw chicken breast on a shallow white foam food tray wrapped in clear film"),
    ("chicken_thigh", "鶏もも肉", "meat", "パック", "raw chicken thigh meat on a shallow white foam food tray wrapped in clear film"),
    ("pork", "豚こま肉", "meat", "パック", "thinly sliced raw pork on a shallow white foam food tray wrapped in clear film"),
    ("mince", "ひき肉", "meat", "パック", "raw ground minced meat on a shallow white foam food tray wrapped in clear film"),
    ("beef", "牛こま肉", "meat", "パック", "thinly sliced raw red beef on a shallow black food tray wrapped in clear film"),
    ("bacon", "ベーコン", "meat", "パック", "strips of bacon"),
    ("sausage", "ウインナー", "meat", "袋", "four small plump pork sausages piled together on a small plate"),
    ("ham", "ハム", "meat", "パック", "round slices of pink ham fanned out"),
    # 魚
    ("salmon", "鮭", "fish", "切れ", "two fillets of raw salmon with orange flesh"),
    ("saba", "さば", "fish", "切れ", "a fillet of mackerel with silver striped skin"),
    ("shirasu", "しらす", "fish", "パック", "a small pile of tiny white boiled whitebait (shirasu) in a small dish"),
    ("tuna_can", "ツナ缶", "fish", "缶", "a small round plain silver tin can of tuna without label"),
    # 卵・乳・大豆製品
    ("eggs", "卵", "dairy", "パック", "a clear plastic egg carton with ten white eggs"),
    ("milk", "牛乳", "dairy", "本", "a plain white milk carton with a blue cap area and no text"),
    ("yogurt", "ヨーグルト", "dairy", "個", "a plain white yogurt cup and a spoon of yogurt"),
    ("cheese", "チーズ", "dairy", "袋", "a wedge of yellow cheese and some cheese slices"),
    ("butter", "バター", "dairy", "個", "a block of pale yellow butter on a small dish"),
    ("tofu", "豆腐", "dairy", "丁", "a white block of tofu in a clear plastic tray with water"),
    ("natto", "納豆", "dairy", "パック", "small square white natto containers stacked, one open showing fermented soybeans"),
    # 米・パン・麺
    ("rice", "お米", "staple", "袋", "a plain kraft paper rice sack with white rice grains spilling out, no text"),
    ("bread", "食パン", "staple", "斤", "a loaf of fluffy Japanese white milk bread (shokupan)"),
    ("udon", "うどん", "staple", "玉", "a bundle of thick white udon noodles"),
    ("pasta", "パスタ", "staple", "袋", "a bundle of dry spaghetti tied with string"),
    # 調味料
    ("soysauce", "しょうゆ", "seasoning", "本", "a plain soy sauce bottle with a red cap and dark sauce, no label text"),
    ("mayo", "マヨネーズ", "seasoning", "本", "a plain squeezable mayonnaise bottle with a red cap, no label text"),
    ("ketchup", "ケチャップ", "seasoning", "本", "a plain squeezable red ketchup bottle, no label text"),
    ("oil", "サラダ油", "seasoning", "本", "a plain clear bottle of golden cooking oil, no label text"),
    ("miso", "みそ", "seasoning", "個", "a round plain container of brown miso paste, lid open"),
    # 冷凍食品
    ("gyoza", "冷凍ぎょうざ", "frozen", "袋", "several pan-fried gyoza dumplings with crispy bottoms"),
    ("icecream", "アイス", "frozen", "個", "a cup of vanilla ice cream with a wooden spoon"),
    # 飲み物
    ("water", "お水", "drink", "本", "a plain clear plastic bottle of water without label"),
    ("tea", "お茶", "drink", "本", "a plain plastic bottle of green tea without label"),
    # 紙製品
    ("toilet_paper", "トイレットペーパー", "paper", "パック", "a stack of white toilet paper rolls"),
    ("tissue", "ティッシュ", "paper", "箱", "a plain box of facial tissues with a tissue popping out, no text"),
    ("kitchen_paper", "キッチンペーパー", "paper", "ロール", "two rolls of white kitchen paper towels"),
    # 洗濯
    ("detergent", "洗濯洗剤", "laundry", "本", "a plain blue liquid laundry detergent bottle with a handle, no label text"),
    ("softener", "柔軟剤", "laundry", "本", "a plain soft pink fabric softener bottle, no label text"),
    # キッチン
    ("dish_soap", "食器用洗剤", "kitchen", "本", "a plain green dish soap bottle and a yellow kitchen sponge with bubbles, no label text"),
    ("wrap", "ラップ", "kitchen", "本", "a box of plastic cling wrap with clear film pulled out, plain box without text"),
    ("foil", "アルミホイル", "kitchen", "本", "a roll of shiny aluminum foil partly unrolled"),
    ("sponge", "スポンジ", "kitchen", "個", "two kitchen sponges, yellow and green"),
    ("trash_bag", "ゴミ袋", "kitchen", "袋", "a roll of semi-transparent white garbage bags"),
    # 掃除
    ("bath_cleaner", "お風呂洗剤", "cleaning", "本", "a plain blue spray bottle of bathroom cleaner, no label text"),
    ("toilet_cleaner", "トイレ洗剤", "cleaning", "本", "a white porcelain toilet bowl next to a plain blue plastic cleaning bottle and a toilet brush, no label text"),
    ("wipes_clean", "除菌シート", "cleaning", "個", "a soft pack of disinfectant wet wipes with one wipe pulled out, no text"),
    # バス・洗面
    ("shampoo", "シャンプー", "bath_body", "本", "a light brown pump bottle of shampoo with a few soap bubbles around it, no label text"),
    ("body_soap", "ボディソープ", "bath_body", "本", "a plain cream colored pump bottle of body wash with soap bubbles, no label text"),
    ("hand_soap", "ハンドソープ", "bath_body", "本", "a small plain foaming hand soap pump bottle with foam, no label text"),
    ("toothpaste", "歯みがき粉", "bath_body", "本", "a plain white toothpaste tube and a toothbrush, no text"),
]

STYLE = (
    "Cute simple flat vector illustration of {item}, a single subject centered with generous empty space around it, "
    "soft rounded shapes, gentle warm muted colors, subtle grainy paper texture, "
    "on a plain flat warm cream beige background, soft small shadow under the object, "
    "cozy Japanese picture-book style, no text, no letters, no numbers, no logo, no watermark."
)


def write_js():
    data = [{"id": i, "name": n, "category": c, "unit": u} for i, n, c, u, _ in CATALOG]
    js = "// tools/catalog.py から生成\nwindow.CATALOG=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (ROOT / "catalog.js").write_text(js, encoding="utf-8")
    print("catalog.js", len(data), "items")


def workflow(prompt, seed):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.0}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
              "latent_image": ["7", 0], "seed": seed, "steps": 9, "cfg": 1.0,
              "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "ouchi_stock"}},
    }


def comfy(path, data=None):
    req = urllib.request.Request(COMFY + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def generate(only):
    from PIL import Image
    out_dir = ROOT / "img"
    out_dir.mkdir(exist_ok=True)
    for i, n, c, u, desc in CATALOG:
        out = out_dir / f"{i}.webp"
        if only and i not in only:
            continue
        if out.exists() and not only:
            continue
        pid = json.loads(comfy("/prompt", {"prompt": workflow(STYLE.format(item=desc), random.randint(1, 2**31))}))["prompt_id"]
        while True:
            hist = json.loads(comfy(f"/history/{pid}"))
            if pid in hist and hist[pid].get("outputs"):
                break
            time.sleep(0.5)
        img = hist[pid]["outputs"]["10"]["images"][0]
        raw = comfy(f"/view?filename={urllib.request.quote(img['filename'])}&subfolder={img['subfolder']}&type=output")
        Image.open(io.BytesIO(raw)).convert("RGB").resize((512, 512), Image.LANCZOS).save(out, "WEBP", quality=82)
        print("ok", i, n, flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "js"
    if cmd == "js":
        write_js()
    elif cmd == "gen":
        generate(set(sys.argv[2:]))
