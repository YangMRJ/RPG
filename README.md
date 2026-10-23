# Grid Quest

Mini RPG de mapa infinito em Python + pygame, com point-and-click, ataques editáveis, hotbar estilo Diablo e combate por turnos opcional.

## Descrição

Você controla um herói num mundo em grid infinito, gerado proceduralmente (água, areia, árvores e pedras). Explore, colete itens, enfrente NPCs em tempo real ou entre em combate por turnos, e edite quase tudo na ficha: atributos, ataques (melee, ranged e magia), armas e itens.

Tudo está em um único arquivo (`grid_quest.py`), sem imagens ou assets externos.

## Requisitos

- Python 3.9+
- pygame 2.x

## Como rodar

```bash
pip install pygame
python grid_quest.py
```

## Controles

| Ação | Controle |
|---|---|
| Mover / atacar o inimigo clicado | Botão esquerdo |
| Disparar o ataque selecionado na direção do cursor | Botão direito |
| Selecionar ataque da hotbar | `1`–`8` ou clique no slot |
| Poção de vida / mana | `Q` / `E` |
| Zoom | Roda do mouse |
| Mover a câmera | Botão do meio (arrastar) ou setas |
| Câmera volta a seguir o herói | `Espaço` |
| Ficha / Ataques / Inventário | `C` / `A` / `I` |
| Iniciar ou encerrar combate por turnos | `T` |
| Fim do turno | `Enter` |
| Salvar / carregar ficha | `F5` / `F9` |
| Reviver (após morrer) | `R` |
| Menu / fechar painel | `Esc` |

## Recursos

- **Menu inicial** com Novo Jogo, Continuar, Controles e Sair.
- **Mapa infinito** gerado por ruído e por hash com semente aleatória a cada jogo. NPCs e itens nascem por chunks (16x16) conforme você explora.
- **Movimentação point-and-click** com pathfinding A* em 8 direções, sem cortar quinas.
- **Ficha, ataques e inventário** num painel com abas. Clique num campo, digite e confirme com Enter. Campos de tipo alternam ao clicar.
- **Ataques editáveis**: nome, tipo (melee, ranged ou magia), dano, alcance, custo de mana, área e cor. Dá para criar e apagar ataques.
- **Barras de HP** sobre cada entidade, além de HP e MP do jogador no HUD.
- **Hotbar de 8 slots** com tooltip, cooldown e indicação de mana insuficiente.
- **Câmera** com zoom ancorado no cursor e pan livre.
- **Combate por turnos** contra NPCs a até 14 tiles. Cada turno tem movimento limitado e 1 ação.
- **Efeitos visuais**: slash em arco para melee (giratório quando a área é maior que 0), projéteis para ranged, orbes com rastro e explosão para magia, e números de dano flutuantes.
- **Itens coletáveis**: poções, ouro e armas. Armas equipadas somam bônus ao tipo de ataque correspondente.

## Regras de jogo

**Dano efetivo** = dano base do ataque + atributo ÷ 2 + bônus das armas equipadas do mesmo tipo.

O atributo usado depende do tipo do ataque: Força para melee, Destreza para ranged e Inteligência para magia. O valor final varia cerca de ±15% a cada golpe.

**Área** (campo de edição do ataque):
- Em melee, valor maior que 0 faz um golpe giratório de 360°.
- Em ranged e magia, valor maior que 0 faz o projétil explodir em área.

**Mana** regenera lentamente fora de combate e +2 a cada turno seu em combate.

**Combate por turnos**
1. A ordem é: jogador primeiro, depois os NPCs por distância (até 6 por combate).
2. No seu turno você tem um orçamento de movimento (campo "Movimento/turno") e 1 ação.
3. Os NPCs se aproximam e atacam. Goblin e esqueleto são melee, o arqueiro é ranged e o mago sombrio usa magia em área.
4. O combate termina quando todos os inimigos morrem, ou quando você aperta `T`.

Fora de combate, os NPCs ficam passivos e vagam, então dá para testar ataques neles em tempo real.

## Save

`F5` salva a ficha (atributos, ataques e inventário) em `ficha.json`, na pasta onde o jogo foi executado. `F9` carrega. O mapa não é salvo: cada Novo Jogo gera um mundo novo.

## Estrutura do código

Um único arquivo, dividido em seções:

| Seção | Conteúdo |
|---|---|
| Mundo infinito | `hsh`, `vnoise`, `terrain`, `astar` |
| Dados | `Attack`, `Ent`, `Player`, templates de NPC e itens |
| `Game` | Geração de chunks, combate e turnos, eventos, update e desenho (mundo, efeitos, HUD, painel) |

## Ideias para evoluir

- Salvar o mundo, os itens coletados e a posição.
- XP e níveis.
- Obstáculos que bloqueiam projéteis (linha de visão).
- Mais tipos de NPC e itens, com drops por tabela.
- Sprites e sons.
