"""
Pipeline de conversão de imagens para WebP.

Uso:
    python tools/convert_images.py

Requisito:
    pip install Pillow

Comportamento:
    - Processa todos os PNG/JPEG em static/imagens/
    - Converte para WebP com qualidade 82
    - Exibe tamanho original, tamanho novo e % de redução
    - Não apaga os originais (validar em produção antes de remover)
"""

import sys
from pathlib import Path

QUALIDADE = 82
EXTENSOES_ORIGEM = {".png", ".jpg", ".jpeg"}
PASTA = Path(__file__).parent.parent / "static" / "imagens"


def converter(arquivo: Path) -> None:
    destino = arquivo.with_suffix(".webp")

    if destino.exists():
        print(f"  [ignorado]  {arquivo.name} → já existe {destino.name}")
        return

    try:
        from PIL import Image  # type: ignore[import]
    except ImportError:
        print(
            "Pillow não instalado. Execute: pip install Pillow",
            file=sys.stderr,
        )
        sys.exit(1)

    tamanho_original = arquivo.stat().st_size

    with Image.open(arquivo) as img:
        # Preserva transparência (RGBA) se existir
        if img.mode in ("RGBA", "LA"):
            img.save(destino, "WEBP", quality=QUALIDADE, lossless=False)
        else:
            img = img.convert("RGB")
            img.save(destino, "WEBP", quality=QUALIDADE)

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
        ja_existia = destino.exists()
        converter(arquivo)
        if not ja_existia and destino.exists():
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
            " Após validar em produção, remova os PNGs/JPEGs."
        )
    else:
        print("\nNenhuma conversão nova realizada.")


if __name__ == "__main__":
    main()
