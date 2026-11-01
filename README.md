# Tab5 + Stream Deck Neo Stand

Stand de mesa impresso em 3D que junta um **M5Stack Tab5** (na horizontal) e um **Elgato Stream Deck Neo** num único console inclinado a 60°.

![Stand com o Tab5 e o Stream Deck Neo](images/stand_with_devices.png)

**STL pronto para imprimir:** [`stl/tab5_neo_stand.stl`](stl/tab5_neo_stand.stl)

## Características

- **60° de inclinação** em relação à mesa, com o Neo embaixo e o Tab5 em cima. O Tab5 fica num degrau de 14 mm, de modo que a frente dos dois aparelhos fica no mesmo plano.
- **Sem borda na frente.** O Neo apoia num lábio de 8 mm e o Tab5 em três abas de 4 mm. Nada fica na frente da tela, das teclas ou das molduras.
- **Bateria do Tab5 Kit (NP-F550):** um rasgo no degrau recebe a bateria, que fica 14,7 mm saliente no verso. O Tab5 também apoia direito sem a bateria, e o rasgo ainda serve para centralizá-lo.
- **Abertura do alto-falante:** o alto-falante do Tab5 fica na borda de baixo, à direita. As abas desviam da grade, que sopra para um vão de 14 mm entre o Tab5 e o Neo, aberto para a frente.
- **Cabos escondidos:** o corpo é oco. O cabo USB-C 90° do Tab5 entra num bolso ao lado da porta, e o cabo fixo do Neo entra por um furo atrás dele. Os dois saem por uma abertura na traseira, rente à mesa.
- **Imprime sem suporte**, em pé, do jeito que fica na mesa.
- Rebaixos para 4 pés de borracha adesivos de Ø10 mm.

| Frente | Traseira | Lateral |
|---|---|---|
| ![Frente](images/stand_front.png) | ![Traseira](images/stand_back.png) | ![Lateral](images/stand_side.png) |

## Impressão

| | |
|---|---|
| Orientação | Como está no STL: em pé, com a base na mesa |
| Suportes | Nenhum (rampas no máximo a 40° da vertical; a maior ponte tem 20 mm, no teto interno) |
| Material | PLA ou PETG |
| Camada | 0,2 mm |
| Paredes | O modelo tem paredes de 2,4 mm. Use 3 ou mais perímetros e 15% de preenchimento |
| Tamanho | 168 × 120,5 × 162 mm |
| Volume | 239 cm³ de sólido (cerca de 300 g de PLA a 100%; menos com 3 perímetros e 15%) |

## Montagem

1. Cole os 4 pés de borracha nos rebaixos da base.
2. **Neo:** dobre o suporte integrado rente às costas. Passe o cabo, com o plugue na frente, pelo furo atrás do Neo, por dentro do stand e para fora pela abertura traseira. Apoie o Neo no lábio de baixo.
3. **Tab5:** passe o cabo USB-C 90° de trás para a frente: entra pela abertura traseira e sai pelo bolso à esquerda do degrau. Ligue o plugue na USB-C do Tab5 (borda esquerda) e apoie o Tab5 nas três abas, com a bateria entrando no rasgo.

### Que cabo USB-C 90° usar

O bolso foi feito para um plugue em ângulo cujo cabo sai **para trás**, perpendicular à tela, e entra direto no corpo do stand. Com um plugue cujo cabo sai para cima ou para baixo, paralelo à borda, o cabo fica aparente ao lado do Tab5.

## Medidas usadas

| Item | Medida | Fonte |
|---|---|---|
| Tab5 | 128 × 80 × 12 mm, cantos R4 | [Desenho oficial M5Stack](https://docs.m5stack.com/en/core/Tab5) |
| Tab5 Kit (com bateria) | 26,7 mm de espessura, ou seja, a bateria sobressai 14,7 mm | [Docs M5Stack](https://docs.m5stack.com/en/core/Tab5) |
| Bateria NP-F550 no verso | 38,2 × 70,4 mm, em x 81,2–119,4 e y 9,5–79,9 mm (vista de frente, origem no canto inferior esquerdo) | [STL oficial M5Stack](https://github.com/m5stack/M5_Hardware/tree/master/Products/C145_Tab5/Structures) |
| Alto-falante | Borda de baixo, x 91,5–110,5 mm | STL oficial M5Stack |
| USB-C | Borda esquerda, centro em y = 40 mm, 2,5 mm da face traseira | STL oficial M5Stack |
| Stream Deck Neo | 107 × 78 × 26 mm, com o suporte dobrado | [Especificação Elgato](https://www.elgato.com/us/en/p/stream-deck-neo-black) |

> **Antes de imprimir:** as medidas do Neo vêm da especificação oficial, e não de um Neo medido com paquímetro. Se o seu Neo com o suporte dobrado não tiver 26 mm de espessura, ajuste `NEO_T` em `generate_stand.py` e gere o STL de novo. O lábio e os furos têm folga, então só o alinhamento entre as frentes muda.

## Personalizar e gerar o STL

O STL é gerado por um script Python paramétrico, que usa [manifold3d](https://github.com/elalish/manifold). Testado com Python 3.13.

```bash
pip install -r requirements.txt
python generate_stand.py          # escreve stl/tab5_neo_stand.stl
python tools/check_fit.py         # confere encaixe, impressão e malha
python tools/render_previews.py   # atualiza as imagens em images/
```

Principais parâmetros, no topo de `generate_stand.py`:

| Parâmetro | Padrão | O que faz |
|---|---|---|
| `TILT` | 60 | Inclinação da face em relação à mesa (graus) |
| `NEO_W`, `NEO_H`, `NEO_T` | 107, 78, 26 | Medidas do Neo com o suporte dobrado |
| `TAB5_GAP` | 14 | Vão entre o topo do Neo e a base do Tab5 (saída do alto-falante) |
| `NEO_LIP` | 8 | Altura do lábio que segura o Neo |
| `TAB_X` | 3 abas | Posição das abas sob o Tab5, em mm a partir da borda esquerda |
| `SIDE` | 20 | Margem de cada lado do Tab5 (espaço do plugue 90°) |
| `USB_SLOT_W`, `USB_SLOT_L` | 17, 44 | Tamanho do bolso do plugue USB-C |
| `WALL`, `FLOOR` | 2,4, 3 | Espessura das paredes e da base |
| `TAB5_MIRROR` | `False` | Espelha os recortes do Tab5, se a USB-C estiver do outro lado |

### O que `tools/check_fit.py` verifica

- O sólido é manifold e a malha do STL não tem vértices coincidentes nem triângulos de área zero.
- Não há interferência com o Tab5, a bateria, o plugue 90° com o cabo, o Neo e o cabo do Neo.
- O caminho entre a grade do alto-falante e o vão está livre.
- Nenhuma parte do stand fica na frente do contorno do Tab5 ou do Neo (aparelhos totalmente à mostra).
- Não há overhang acima de 45°, e as pontes ficam abaixo de 25 mm.

O script baixa sob demanda o modelo oficial do Tab5 (repositório M5_Hardware da M5Stack) para `.cache/`. Ele é usado apenas nas imagens e não faz parte deste repositório.

## Estrutura

```
generate_stand.py        modelo paramétrico -> stl/tab5_neo_stand.stl
stl/                     STL pronto para imprimir
tools/devices.py         envelopes do Tab5, da bateria, do plugue e do Neo
tools/check_fit.py       verificação de encaixe, impressão e malha
tools/render_previews.py imagens do README
images/                  previews renderizados
```

## English summary

A 3D-printable desk stand that holds an M5Stack Tab5 in landscape above an Elgato Stream Deck Neo, both on a 60° slope with their front faces flush. Neither device has a bezel in front of it. The Tab5's NP-F550 battery drops into a notch, and its bottom-edge speaker vents into an open gap. The hollow body hides both cables (90° USB-C for the Tab5, the Neo's captive cable), which leave through a rear opening. It prints upright with no supports. Download [`stl/tab5_neo_stand.stl`](stl/tab5_neo_stand.stl), or edit `generate_stand.py` and run it to regenerate.
