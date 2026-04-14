# Curse of Strahd — VTT

Virtual Tabletop para a campanha Curse of Strahd (D&D 5e).
Feito em Python + Pygame. Multiplayer via WebSockets.

---

## Instalação

```bash
pip install pygame websockets
```

## Rodar

```bash
python main.py
```

---

## Estrutura

```
strahd_vtt/
├── main.py                    # Ponto de entrada
├── requirements.txt
├── settings.json              # Gerado automaticamente
├── assets/
│   ├── fonts/                 # Coloque as fontes aqui (ver abaixo)
│   ├── images/
│   ├── sounds/
│   └── music/
├── data/
│   ├── characters/            # characters.json gerado automaticamente
│   └── compendium/
│       ├── section_a.json     # NPCs
│       ├── section_b.json     # Monstros
│       ├── section_c.json     # Itens
│       └── ...                # Adicione mais conforme necessário
└── src/
    ├── app.py                 # Controlador central + loop principal
    ├── constants.py           # Cores, tamanhos, nomes de cenas
    ├── fonts.py               # Gerenciador de fontes
    ├── settings.py            # Persistência de configurações
    ├── ui/
    │   ├── atmosphere.py      # Partículas e efeitos de fundo
    │   ├── widgets.py         # MenuItem, Button, Slider, Dropdown, TextInput
    │   ├── scene_menu.py      # Menu principal
    │   ├── scene_play_select.py  # Mestrar / Jogar
    │   ├── scene_lobby.py     # Lobby multiplayer
    │   ├── scene_characters.py   # Lista de personagens
    │   ├── scene_char_create.py  # Criação de personagem
    │   ├── scene_compendium.py   # Compêndio A-I
    │   └── scene_options.py      # Opções gráficas e de áudio
    └── network/
        ├── server.py          # Servidor WebSocket (daemon thread)
        └── client.py          # Cliente WebSocket
```

---

## Fontes Recomendadas (gratuitas — Google Fonts)

Coloque em `assets/fonts/`:

| Arquivo                          | Uso          | Link                                    |
|----------------------------------|--------------|-----------------------------------------|
| `UnifrakturMaguntia-Book.ttf`    | Título gótico | fonts.google.com/specimen/UnifrakturMaguntia |
| `Cinzel-Regular.ttf`             | Menus/títulos | fonts.google.com/specimen/Cinzel        |
| `EBGaramond-Regular.ttf`         | Corpo de texto | fonts.google.com/specimen/EB+Garamond  |

Sem as fontes o jogo usa fallback do sistema — funciona, mas fica menos temático.

---

## Multiplayer

### Mestrar (hospedar)
1. Abra o jogo → Jogar → Mestrar → Iniciar Servidor
2. Compartilhe seu IP local com os jogadores (ex: `192.168.1.10`)
3. Porta padrão: `5740`

### Jogar (conectar)
1. Abra o jogo → Jogar → Jogar
2. Digite o IP do mestre, a porta e seu nome
3. Clique em Conectar

Para jogar pela internet use ngrok ou configure port forwarding no roteador.

---

## Compêndio — Adicionar Conteúdo

Crie/edite JSONs em `data/compendium/`:

```json
[
  {
    "name": "Nome do Item",
    "type": "Categoria",
    "rarity": "Raridade / CR",
    "source": "Livro p.XX",
    "description": "Texto completo..."
  }
]
```

Seções disponíveis: `section_a.json` a `section_i.json`

---

## Próximos Passos (roadmap)

- [ ] Mapa top-down com tokens arrastáveis
- [ ] Rolagem de dados integrada ao chat
- [ ] Fichas de personagem completas (atributos, magias, inventário)
- [ ] Névoa de guerra no mapa
- [ ] Importação de mapas (PNG/JPG)
- [ ] Iniciativa e tracker de combate
- [ ] Notas do mestre (visíveis só pro DM)
