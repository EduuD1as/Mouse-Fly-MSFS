# Mouse-Fly MSFS

<img src="assets/icon.png" width="96" align="right" alt="ícone">

Use o mouse como joystick no **Microsoft Flight Simulator 2020/2024**.

- Movimento do mouse controla o manche (aileron e profundor)
- Clique esquerdo, direito, clique da rodinha, **Mouse 4** e **Mouse 5** (botões laterais) viram botões do joystick
- A rodinha pode virar botões (para cima/para baixo) ou o acelerador
- Tecla **F8** liga e desliga, mesmo com o jogo em tela cheia
- Cada opção do programa tem um **?** explicando o que faz

![screenshot](docs/screenshot.png)

## Download

**[⬇ Baixar Mouse-Fly-MSFS.exe](https://github.com/EduuD1as/Mouse-Fly-MSFS/raw/main/Mouse-Fly-MSFS.exe)**

Não precisa instalar: é só abrir o `.exe`.

## Antes de usar: instale o vJoy

O Mouse-Fly usa o **vJoy**, um joystick virtual gratuito.

1. Baixe e instale o vJoy: https://github.com/BrunnerInnovation/vJoy/releases
2. Abra o programa **Configure vJoy** (vem junto com o vJoy).
3. No dispositivo **1**, deixe marcados os eixos **X**, **Y** e **Z**, e coloque **Number of Buttons: 8**.
4. Clique em **Apply**.

## Como usar

1. Abra o `Mouse-Fly-MSFS.exe`.
2. Aperte **F8** para ligar (o botão no topo fica verde).
3. No MSFS, vá em **Opções → Controles** e escolha o dispositivo **vJoy Device**.
4. Associe:
   - **Eixo X** → Aileron
   - **Eixo Y** → Elevator (profundor)
   - **Botões 1 a 7** → o que você quiser (flaps, trem de pouso, freio, trim...)
   - **Eixo Z** → Throttle, se ativou "Scroll → eixo Z"
5. Aperte **F8** de novo para desligar e usar o mouse normalmente nos menus.

| Mouse | Joystick |
|-------|----------|
| Clique esquerdo | Botão 1 |
| Clique direito | Botão 2 |
| Clique da rodinha | Botão 3 |
| Mouse 4 (lateral) | Botão 4 |
| Mouse 5 (lateral) | Botão 5 |
| Rodinha para cima | Botão 6 |
| Rodinha para baixo | Botão 7 |

## Problemas comuns

- **"vJoy ocupado por outro programa"**: feche outros programas de mouse/joystick (e outras janelas do Mouse-Fly).
- **"vJoyInterface.dll não encontrada"**: o vJoy não está instalado.
- **Não funciona com o jogo aberto**: se o MSFS roda como administrador, abra o Mouse-Fly como administrador também.
- **Antivírus bloqueou**: alguns antivírus dão falso positivo em programas que leem o mouse. O código-fonte está todo neste repositório.

## Licença

MIT
