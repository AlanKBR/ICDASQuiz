"""
Pipeline de normalização de imagens clínicas para WebP.

Uso:
    python tools/convert_images.py

Requisito:
    pip install Pillow

Comportamento:
    - Processa PNG/JPEG em static/imagens/;
    - Corrige orientação EXIF;
    - Reduz apenas imagens acima de 1280x720, preservando proporção;
    - Converte para WebP com qualidade 86 (method=6);
    - Não carrega EXIF/metadata para o arquivo servido;
    - Exibe tamanho original, tamanho novo e redução;
    - Não apaga os originais.
"""

import sys
from pathlib import Path

QUALIDADE = 86
METHOD = 6
MAX_RESOLUCAO = (1280, 720)
EXTENSOES_ORIGEM = {".png", ".jpg", ".jpeg"}
PASTA = Path(__file__).parent.parent / "static" / "imagens"


def converter(arquivo: Path) -> None:
    destino = arquivo.with_suffix(".webp")

    try:
        from PIL import Image, ImageOps  # type: ignore[import]
    except ImportError:
        print(
            "Pillow não instalado. Execute: pip install Pillow",
            file=sys.stderr,
        )
        sys.exit(1)

    tamanho_original = arquivo.stat().st_size

    with Image.open(arquivo) as origem:
        img = ImageOps.exif_transpose(origem)
        img.thumbnail(MAX_RESOLUCAO, Image.Resampling.LANCZOS)

        # Uma conversão explícita evita propagar metadata do arquivo de origem.
        if img.mode in ("RGBA", "LA"):
            normalizada = img.convert("RGBA")
        else:
            normalizada = img.convert("RGB")

        normalizada.save(
            destino,
            "WEBP",
            quality=QUALIDADE,
            method=METHOD,
            lossless=False,
        )

    tamanho_novo = destino.stat().st_size
    reducao = (1 - tamanho_novo / tamanho_original) * 100
    kb_antes = tamanho_original / 1024
    kb_depois = tamanho_novo / 1024

    print(
        f"  [ok]  {arquivo.name}"
        f"  {kb_antes:.1f} KB → {kb_depois:.1f} KB"
        f"  ({reducao:.1f}% menor)"
    )


def main() -> None:
    if not PASTA.exists():
        print(f"Pasta não encontrada: {PASTA}", file=sys.stderr)
        sys.exit(1)

    arquivos = sorted(
        f for f in PASTA.iterdir()
        if f.suffix.lower() in EXTENSOES_ORIGEM
    )

    if not arquivos:
        print(f"Nenhum PNG/JPEG encontrado em {PASTA}")
        return

    print(f"Convertendo {len(arquivos)} imagem(ns) em {PASTA}\n")

    total_antes = 0
    total_depois = 0

    for arquivo in arquivos:
        destino = arquivo.with_suffix(".webp")
        converter(arquivo)
        if destino.exists():
            total_antes += arquivo.stat().st_size
            total_depois += destino.stat().st_size

    if total_antes > 0:
        reducao_total = (1 - total_depois / total_antes) * 100
        kb_a = total_antes / 1024
        kb_d = total_depois / 1024
        print(
            f"\nTotal: {kb_a:.1f} KB → {kb_d:.1f} KB"
            f" ({reducao_total:.1f}% de redução)"
        )
        print(
            "\nOriginais mantidos."
            " Após validar os WebPs, remova os PNGs/JPEGs."
        )
    else:
        print("\nNenhuma conversão nova realizada.")


if __name__ == "__main__":
    main()
