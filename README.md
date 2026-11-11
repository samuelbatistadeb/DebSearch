# DebSearch — Guia de implantação em um computador Windows

Este documento apresenta o procedimento para instalar e iniciar o DebSearch em um computador novo, que será responsável por hospedar o sistema e disponibilizá-lo aos colaboradores da empresa.

O objetivo é realizar a implantação do zero, preparando o Python, instalando as dependências, configurando o banco de dados, criando o administrador, catalogando os documentos e iniciando a aplicação.

> **Importante:** faça a implantação em uma pasta separada. Não apague nem substitua o banco de dados utilizado nos testes até confirmar que a nova instalação está funcionando corretamente.

---

## 1. Estrutura prevista do projeto

A instalação deverá manter a seguinte organização:

```text
C:\DebSearch\
│
├── database\
│   └── catalogo.db
│
├── static\
│   ├── index.html
│   ├── css\
│   │   └── style.css
│   └── js\
│       └── app.js
│
├── .venv\
│
├── app.py
├── banco.py
├── configuracao.py
├── indexador.py
├── monitor.py
├── pesquisa.py
├── preparar_fts.py
├── usuarios.py
├── criar_admin.py
├── gerenciar_usuarios.py
├── seguranca_login.py
└── requirements.txt
```

A estrutura é uma referência. Devem ser mantidos os nomes e caminhos que realmente existem no projeto atual.

A pasta `.venv` será criada novamente no computador novo, não devendo ser copiada do computador de desenvolvimento.

---

## 2. Dependências necessárias

### 2.1 Requisitos do computador

- Windows 10 ou Windows 11.
- Python instalado.
- Acesso administrativo ao computador para instalações e configurações de rede.
- Acesso de leitura à pasta compartilhada das notas fiscais.
- Espaço disponível para armazenar o banco de dados e os arquivos do projeto.

### 2.2 Bibliotecas Python

| Biblioteca | Finalidade |
|---|---|
| `fastapi` | Estrutura da aplicação web |
| `uvicorn[standard]` | Execução do servidor FastAPI |
| `pwdlib[argon2]` | Proteção das senhas dos usuários |
| `itsdangerous` | Assinatura e proteção das sessões |
| `watchdog` | Monitoramento de alterações nos arquivos, caso utilizado pelo monitor |

O SQLite e o FTS5 são utilizados por meio do módulo `sqlite3` do próprio Python. Não é necessário instalar um servidor SQLite separado.

### 2.3 Arquivo requirements.txt

Criar um arquivo chamado `requirements.txt` na pasta principal do projeto com o seguinte conteúdo:

```text
fastapi
uvicorn[standard]
pwdlib[argon2]
itsdangerous
watchdog
```

A lista deverá ser conferida com os imports dos arquivos atuais antes da instalação. Se algum pacote não for utilizado, poderá ser removido; se houver outras bibliotecas externas nos códigos, deverão ser adicionadas.

---

## 3. Preparação do computador novo

### Etapa 1 — Instalar Python

Instalar o Python no computador que hospedará o DebSearch.

Durante a instalação, marcar a opção:

**Add Python to PATH**

Após a instalação, abrir o PowerShell e executar:

```powershell
python --version
```

Depois:

```powershell
python -m pip --version
```

Se os comandos funcionarem, o Python está disponível.

### Etapa 2 — Criar a pasta do projeto

Criar:

```text
C:\DebSearch
```

Copiar todos os arquivos do projeto para essa pasta, mantendo a estrutura de diretórios.

Não copiar a pasta `.venv` do computador antigo.

### Etapa 3 — Criar o ambiente virtual

Abrir o PowerShell e executar:

```powershell
cd C:\DebSearch
```

Criar o ambiente virtual:

```powershell
python -m venv .venv
```

Ativar:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação, utilizar o Prompt de Comando:

```bat
.venv\Scripts\activate.bat
```

### Etapa 4 — Instalar as dependências

Com o ambiente virtual ativado:

```powershell
python -m pip install --upgrade pip
```

Depois:

```powershell
python -m pip install -r requirements.txt
```

Conferir as bibliotecas instaladas:

```powershell
python -m pip list
```

---

## 4. Configuração inicial

Antes de executar os arquivos, abrir `configuracao.py` e conferir as configurações.

### 4.1 Pasta de origem

Definir o caminho da pasta compartilhada onde estão armazenadas as notas fiscais.

Exemplo:

```text
\\192.168.0.0\Users\Desktop\exemplo
```

O caminho definitivo deverá ser confirmado no computador novo.

### 4.2 Banco de dados

O banco deverá ficar no disco local do computador que hospeda o DebSearch:

```text
C:\DebSearch\database\catalogo.db
```

Não colocar o banco SQLite diretamente na pasta compartilhada para que vários computadores o abram simultaneamente.

Os colaboradores acessarão o banco exclusivamente pela aplicação.

### 4.3 Chave secreta
Execultar no terminal para gerar a chave: 

```text
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Configurar uma chave secreta forte e exclusiva para a instalação de produção.

Não utilizar uma chave de exemplo ou deixar uma chave pública fixa no código.

Preferencialmente, a chave deverá ser fornecida por variável de ambiente, conforme a configuração utilizada pelo projeto.

### 4.4 Cookies seguros

A configuração `COOKIE_SEGURO` deverá ser:

- `False` durante os primeiros testes locais por HTTP.
- `True` quando o acesso estiver configurado corretamente com HTTPS.

Não ativar cookies seguros antes de configurar HTTPS, pois o navegador poderá deixar de enviar o cookie durante os testes por HTTP.

### 4.5 Acesso à pasta compartilhada

O computador que executará o DebSearch precisa ter permissão para ler e listar os arquivos da pasta compartilhada.

É importante testar o acesso usando a mesma conta do Windows que executará a aplicação.

Se futuramente o sistema for configurado como serviço do Windows, será necessário garantir que a conta do serviço também tenha acesso ao compartilhamento.

---

## 5. Ordem de execução dos arquivos

Esta é a sequência recomendada para uma instalação nova, com banco de dados vazio.

### 1º — Inicializar o banco de dados

Executar:

```powershell
python banco.py
```

Esse arquivo cria as tabelas e estruturas necessárias para o funcionamento do sistema.

Conferir se o banco foi criado em:

```text
C:\DebSearch\database\catalogo.db
```

### 2º — Criar o administrador inicial

Executar:

```powershell
python criar_admin.py
```

Informar o nome de usuário e a senha solicitados.

Utilizar uma senha forte, com pelo menos 12 caracteres.

O administrador será responsável pelo gerenciamento das contas dos colaboradores.

### 3º — Preparar a pesquisa FTS5

Executar, conforme o comportamento previsto no script:

```powershell
python preparar_fts.py
```

Esse procedimento prepara a estrutura de pesquisa textual utilizada pelo DebSearch.

**Atenção:** antes de executar, conferir o código para garantir que ele não apague registros existentes nem recrie desnecessariamente as tabelas principais.

Se o script tiver sido desenvolvido para preparar um banco vazio, executá-lo antes da catalogação inicial.

### 4º — Catalogar os documentos

Executar:

```powershell
python indexador.py
```

Esse processo fará a leitura da pasta de notas fiscais e cadastrará os arquivos encontrados no banco de dados.

A catalogação inicial poderá levar alguns minutos, dependendo da quantidade de documentos, da velocidade da rede e do disco.

Ao terminar, conferir:

- Quantidade de arquivos encontrados.
- Quantidade de novos registros cadastrados.
- Quantidade de registros atualizados.
- Possíveis erros durante a leitura.

Não executar novamente sem entender o comportamento do indexador e confirmar se ele atualiza registros ou pode gerar duplicidades.

### 5º — Iniciar a aplicação

Executar:

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Abrir no navegador do próprio computador:

```text
http://127.0.0.1:8000
```

Realizar os testes de login e pesquisa.

O endereço `127.0.0.1` permite acesso somente pelo próprio computador. Ainda não libera o sistema para os colaboradores.

Para encerrar a aplicação, pressionar `Ctrl + C` no terminal.

### 6º — Cadastrar os colaboradores

Abrir outro PowerShell na pasta do projeto, ativar o ambiente virtual e executar:

```powershell
python gerenciar_usuarios.py
```

Utilizar o menu para:

1. Cadastrar usuários.
2. Listar usuários.
3. Desativar usuários.
4. Reativar usuários.
5. Redefinir senhas.

Não haverá cadastro público pela página de login.

Cada colaborador deverá possuir seu próprio usuário e senha.

---

## 6. Testes antes de liberar o sistema

Antes de disponibilizar o DebSearch aos colaboradores, realizar os seguintes testes:

- [ ] A página inicial abre normalmente.
- [ ] O administrador consegue realizar login.
- [ ] Uma senha incorreta é recusada.
- [ ] Um usuário inexistente é recusado.
- [ ] O bloqueio por tentativas repetidas funciona.
- [ ] A proteção CSRF funciona.
- [ ] A pesquisa retorna documentos esperados.
- [ ] A pesquisa não funciona sem autenticação.
- [ ] A abertura e transferência de arquivos funciona.
- [ ] O sistema impede acesso a caminhos fora da pasta autorizada.
- [ ] O logout encerra a sessão.
- [ ] Um novo usuário consegue entrar.
- [ ] Um usuário desativado não consegue entrar.
- [ ] A aplicação volta a funcionar após ser encerrada e iniciada novamente.

---

## 7. Liberação do acesso pela rede

Somente depois dos testes locais, iniciar a configuração de acesso pela rede.

### Etapas

1. Definir um IP fixo ou reserva DHCP para o computador servidor.
2. Configurar HTTPS para proteger as credenciais e sessões.
3. Ativar `COOKIE_SEGURO=True` após a configuração HTTPS.
4. Configurar as regras do Firewall do Windows.
5. Permitir somente o tráfego necessário da rede interna.
6. Alterar o endereço de escuta do Uvicorn.

Exemplo:

```powershell
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Esse comando faz a aplicação escutar nas interfaces de rede do computador.

**Não liberar o acesso definitivo pela rede utilizando HTTP sem proteção.** A configuração de HTTPS, cookies seguros e Firewall deverá estar concluída antes da utilização pelos colaboradores.

Os usuários acessarão o sistema pelo navegador, utilizando o endereço do computador servidor.

Exemplo:

```text
https://IP-OU-NOME-DO-SERVIDOR/
```

---

## 8. Inicialização automática

Durante os testes, a aplicação poderá ser iniciada manualmente pelo PowerShell.

Para uso diário, o ideal é configurar a inicialização automática junto com o Windows, utilizando um serviço do Windows.

Antes disso, definir:

- Conta do Windows que executará a aplicação.
- Permissões dessa conta na pasta compartilhada.
- Caminho do Python dentro do ambiente virtual.
- Diretório de trabalho do projeto.
- Variáveis de ambiente necessárias.
- Local de armazenamento dos logs.

Não presumir que um serviço executado como `SYSTEM` terá acesso à pasta compartilhada.

---

## 9. Backup e manutenção

O banco de dados deverá possuir uma rotina de backup periódico.

Como o SQLite pode utilizar arquivos auxiliares `-wal` e `-shm`, não copiar simplesmente o arquivo `catalogo.db` enquanto a aplicação estiver em execução.

Para realizar um backup consistente, utilizar o mecanismo de backup do SQLite ou interromper a aplicação e garantir que o banco tenha sido fechado corretamente antes da cópia.

Também devem ser protegidos:

- Arquivo de configuração.
- Chave secreta.
- Credenciais administrativas.
- Banco de dados.
- Logs operacionais.

O banco SQLite deverá permanecer local no computador servidor.

---

## 10. Resumo da sequência de comandos

Após copiar os arquivos, configurar `configuracao.py` e criar `requirements.txt`, a sequência básica será:

```powershell
# 1. Entrar na pasta do projeto
cd C:\DebSearch

# 2. Criar o ambiente virtual
python -m venv .venv

# 3. Ativar o ambiente virtual
.\.venv\Scripts\Activate.ps1

# 4. Atualizar o pip
python -m pip install --upgrade pip

# 5. Instalar as dependências
python -m pip install -r requirements.txt

# 6. Inicializar o banco
python banco.py

# 7. Preparar a pesquisa FTS5
python preparar_fts.py

# 8. Criar o administrador
python criar_admin.py

# 9. Catalogar os documentos
python indexador.py

# 10. Iniciar a aplicação para teste local
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Em outro terminal, para cadastrar os colaboradores:

```powershell
cd C:\DebSearch
.\.venv\Scripts\Activate.ps1
python gerenciar_usuarios.py
```

---

## 11. Pendências antes da implantação definitiva

- [ ] Confirmar se o computador utiliza Windows 10 ou Windows 11.
- [ ] Confirmar o caminho definitivo da pasta compartilhada.
- [ ] Conferir as permissões da conta que executará o DebSearch.
- [ ] Conferir os imports e fechar a lista de dependências.
- [ ] Conferir o comportamento de `preparar_fts.py`.
- [ ] Conferir o comportamento de `indexador.py`.
- [ ] Configurar HTTPS.
- [ ] Definir IP ou nome de rede do servidor.
- [ ] Configurar o Firewall.
- [ ] Configurar inicialização automática.
- [ ] Definir rotina de backup.

**Recomendação final:** realizar a implantação em etapas. Primeiro, deixar o DebSearch funcionando localmente no computador novo. Depois, validar o acesso à pasta compartilhada e os resultados da pesquisa. Por último, configurar HTTPS, acesso pela rede e inicialização automática.


Ótimo. Então já temos a estrutura necessária:
- Projeto: C:\DebDocs
- Python do ambiente virtual: C:\DebDocs\.venv\Scripts\python.exe
- Aplicação: app.py
- Monitor: monitor.py
Vamos manter os dois processos separados. Assim, se o monitor apresentar algum problema, a aplicação web não precisa parar junto com ele.

Antes de instalar os serviços, vamos preparar e testar os comandos que o Windows executará.

Agora precisamos considerar um detalhe importante da infraestrutura: o DebDocs acessa uma pasta compartilhada por rede (\\192.168.0.134\...).

Se iniciarmos o monitor como serviço usando a conta padrão do Windows, ele poderá perder acesso a essa pasta. Por isso, quero configurar a execução com uma conta que tenha permissão de leitura na origem.

Uma pequena decisão de arquitetura: vamos usar o Agendador de Tarefas do Windows, em vez de instalar uma ferramenta externa como NSSM. Ele permite iniciar os dois processos na inicialização, mesmo sem alguém entrar na área de trabalho, e configurar tentativas de recuperação.
Etapa 2 — Verificar a conta e o acesso à pasta
Abra o PowerShell no computador servidor e execute:
Write-Host "=== CONTA DO WINDOWS ==="
whoami

Write-Host "`n=== ACESSO À PASTA DE ORIGEM ==="
Test-Path "\\192.168.0.134\Users\contabilidade\Desktop\@ NOTAS FISCAIS"

Write-Host "`n=== IDENTIFICAÇÃO DO COMPUTADOR ==="
$env:COMPUTERNAME


Precisamos confirmar que a conta que executará as tarefas consegue acessar a pasta de origem.

Depois disso, vamos criar dois arquivos de inicialização dentro de C:\DebDocs, configurar os registros no Agendador de Tarefas e deixar ambos com inicialização automática e recuperação em caso de falha.

O resultado será um DebDocs que funciona em segundo plano, sem precisar abrir o VS Code ou deixar terminais abertos.











Converter em PDF

Isso também pode interessar a você.


Anúncio
Opções do anúncio



Saiba mais
















tudo certo, sigamos












Pensou por 15s

Configurou a inicialização automática e ajustou tarefas do Windows










Ótimo. Vamos preparar os dois inicializadores, com registro de logs. Depois vamos cadastrá-los no Agendador de Tarefas do Windows.

A ideia é que cada processo tenha seu próprio arquivo de inicialização. Isso facilita identificar problemas e reiniciar um sem afetar o outro.
Etapa 3 — Criar os inicializadores
Vamos criar esta estrutura:
C:\DebDocs
│
├── app.py
├── monitor.py
├── banco.py
├── configuracao.py
├── .venv
│
├── logs
│   ├── uvicorn.log
│   └── monitor.log
│
├── iniciar_web.bat
└── iniciar_monitor.bat


1. Criar iniciar_web.bat
Abra o PowerShell e execute:
@'
@echo off
cd /d C:\DebDocs

if not exist logs mkdir logs

.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8000 >> logs\uvicorn.log 2>&1
'@ | Set-Content -Path "C:\DebDocs\iniciar_web.bat" -Encoding ASCII


Esse arquivo inicia o Uvicorn e registra as mensagens em logs\uvicorn.log.
2. Criar iniciar_monitor.bat
Execute:
@'
@echo off
cd /d C:\DebDocs

if not exist logs mkdir logs

.venv\Scripts\python.exe monitor.py >> logs\monitor.log 2>&1
'@ | Set-Content -Path "C:\DebDocs\iniciar_monitor.bat" -Encoding ASCII


Esse arquivo inicia o monitor e registra suas mensagens em logs\monitor.log.
3. Conferir se os arquivos foram criados
Execute:
Get-ChildItem C:\DebDocs\iniciar_*.bat


4. Testar os inicializadores
Abra dois terminais PowerShell separados.

No primeiro:
C:\DebDocs\iniciar_web.bat


No segundo:
C:\DebDocs\iniciar_monitor.bat


Confira se:
- O DebDocs abre normalmente pelo navegador em http://IP-DO-SERVIDOR:8000.
- O monitor inicia sem erros e reconhece a pasta de origem.
- Os arquivos de log são criados dentro de C:\DebDocs\logs.
Se algum dos processos já estiver em execução, não inicie outra instância na mesma porta ou no mesmo monitoramento.

Faça essa etapa e me confirme se os dois inicializadores funcionaram. Depois configuraremos o Agendador de Tarefas para iniciar ambos automaticamente com o Windows e reiniciá-los caso apresentem falhas.











Converter em PDF






certo sigamos













Perfeito. Agora vamos configurar a inicialização automática pelo Agendador de Tarefas do Windows.

Vamos fazer isso de forma que:
- O Uvicorn inicie quando o computador ligar.
- O monitor inicie automaticamente, com um pequeno atraso para dar tempo de a rede e a pasta compartilhada ficarem disponíveis.
- Os dois processos possam funcionar mesmo sem ninguém conectado ao Windows.
- O Windows tente reiniciar os processos se eles encerrarem inesperadamente.
Importante: usaremos a mesma conta do Windows que você verificou no teste de acesso à pasta compartilhada. Isso é especialmente importante para o monitor.
Etapa 4 — Preparar o Agendador
Primeiro, encerre os dois testes manuais, pressionando Ctrl + C nos terminais em que estão rodando. Assim evitamos iniciar uma segunda instância da aplicação ou do monitor.
1. Criar a tarefa da aplicação web
1. Pressione Win + R.
2. Digite taskschd.msc e pressione Enter.
3. No painel direito, clique em Criar Tarefa (não escolha Criar Tarefa Básica).
Na aba Geral, configure:
Campo	Valor
Nome	DebDocs - Aplicacao Web
Descrição	Inicialização automática do servidor web DebDocs
Conta	A mesma conta do teste anterior
Opção de execução	Executar independentemente de o usuário estar conectado

Marque também Executar com privilégios mais altos.

Na aba Disparadores:
1. Clique em Novo.
2. Em iniciar a tarefa, selecione Na inicialização.
3. Deixe habilitada e confirme.
Na aba Ações:
1. Clique em Novo.
2. Ação: Iniciar um programa.
3. Programa/script:
C:\Windows\System32\cmd.exe


4. Adicionar argumentos:
/c "C:\DebDocs\iniciar_web.bat"


5. Iniciar em:
C:\DebDocs


Na aba Condições:
- Desmarque a opção de iniciar somente se estiver conectado à energia, caso apareça.
- Não coloque restrição de rede nesta primeira configuração.
Na aba Configurações:
- Marque Permitir que a tarefa seja executada sob demanda.
- Marque Se a tarefa falhar, reiniciar a cada: 1 minuto.
- Configure para tentar reiniciar 3 vezes.
- Em caso de tarefa já em execução, selecione Não iniciar uma nova instância.
Clique em OK. O Windows poderá solicitar a senha da conta escolhida. Isso é esperado quando configuramos a execução sem usuário conectado.

Atenção: use a senha da conta do Windows, não a senha do DebDocs.
2. Criar a tarefa do monitor
Depois de salvar a primeira tarefa, repita o procedimento com estas diferenças:
Campo	Valor
Nome	DebDocs - Monitor
Descrição	Monitoramento e reconciliação do catálogo
Disparador	Na inicialização
Atraso do disparador	1 minuto
Programa	C:\Windows\System32\cmd.exe
Argumentos	/c "C:\DebDocs\iniciar_monitor.bat"
Iniciar em	C:\DebDocs

Mantenha as mesmas configurações de conta e recuperação da primeira tarefa.

Por enquanto, não reinicie o computador. Primeiro me confirme se conseguiu criar as duas tarefas e se ambas aparecem na Biblioteca do Agendador de Tarefas. Depois faremos o teste controlado de inicialização e verificaremos os logs.

Perfeito. Agora vamos fazer um teste controlado das duas tarefas, antes de reiniciar o servidor. Queremos confirmar que o Agendador realmente mantém os processos em execução, e não apenas inicia e encerra os arquivos .bat.
Etapa 5 — Testar as tarefas
1. Iniciar os dois processos pelo Agendador
Abra o Agendador de Tarefas (taskschd.msc).

Na Biblioteca do Agendador:
1. Localize DebDocs - Aplicacao Web.
2. Clique com o botão direito e selecione Executar.
3. Faça o mesmo com DebDocs - Monitor.
Aguarde aproximadamente 30 segundos.
2. Verificar o estado das tarefas
Abra um PowerShell e execute:
Get-ScheduledTask -TaskName "DebDocs - Aplicacao Web","DebDocs - Monitor" |
    Select-Object TaskName, State

Get-ScheduledTaskInfo -TaskName "DebDocs - Aplicacao Web"
Get-ScheduledTaskInfo -TaskName "DebDocs - Monitor"


O esperado é:

Running
 As duas tarefas devem aparecer como Running.

Um detalhe: o código 0x41301 em LastTaskResult também é normal nesse caso: significa que a tarefa ainda está em execução.
3. Conferir os logs
Execute:
Write-Host "=== LOG DA APLICACAO ==="
Get-Content C:\DebDocs\logs\uvicorn.log -Tail 20

Write-Host "`n=== LOG DO MONITOR ==="
Get-Content C:\DebDocs\logs\monitor.log -Tail 20


Na aplicação, queremos encontrar uma mensagem indicando que o Uvicorn está ativo na porta 8000.

No monitor, queremos encontrar a inicialização e a confirmação de que a reconciliação foi concluída.
4. Testar o acesso
No próprio servidor, abra:

http://127.0.0.1:8000

Depois, teste também pelo IP do servidor, usando outro computador da rede.

Ainda não reinicie o computador.

Me envie:
- O estado das duas tarefas.
- O resultado dos logs.
- Se conseguiu abrir o DebDocs pelo navegador.
Depois vamos conferir as opções de execução prolongada e recuperação de falhas e, finalmente, fazer o teste de reinicialização do Windows.











Converter em PDF

Para hospedagem e infra de servidores, aqui vai uma opção Brasil.


Anúncio
Opções do anúncio



Saiba mais
















tudo certo, sigamos













Excelente! Agora os dois processos já estão funcionando pelo Agendador. Vamos fazer a última configuração antes do teste de reinicialização: garantir que as tarefas não sejam encerradas por limites de tempo e que o Windows tente recuperá-las em caso de falha.
Etapa 6 — Ajustar a execução contínua
Abra o Agendador de Tarefas (taskschd.msc).

Faça isso para as duas tarefas: DebDocs - Aplicacao Web e DebDocs - Monitor.
1. Aba Configurações
Clique duas vezes na tarefa e abra Configurações.

Confira:
Opção	Configuração
Permitir execução sob demanda	Marcada
Executar tarefa o mais rápido possível após uma inicialização agendada perdida	Marcada
Se a tarefa falhar, reiniciar a cada	1 minuto
Tentar reiniciar até	3 vezes
Interromper a tarefa se ela for executada por mais de	Desmarcada
Se a tarefa não terminar quando solicitada	Não forçar encerramento, se disponível
Se a tarefa já estiver em execução	Não iniciar uma nova instância

2. Aba Condições
Confira:
- Não exigir que o computador esteja ocioso.
- Não exigir alimentação externa, caso seja um notebook.
- Não restringir a execução por condição de rede.
3. Aba Geral
Confirme:
- Executar independentemente de o usuário estar conectado.
- Executar com privilégios mais altos.
- Conta do Windows correta.
Clique em OK e repita na outra tarefa.
Etapa 7 — Testar a inicialização automática
Agora vamos testar o funcionamento real.
1. Salve tudo o que estiver aberto no servidor.
2. Reinicie o Windows normalmente.
3. Não abra VS Code, PowerShell ou os arquivos .bat.
4. Aguarde aproximadamente 2 minutos após o Windows iniciar.
5. Em outro computador, tente acessar o DebDocs pelo endereço:
http://IP-DO-SERVIDOR:8000


Depois, no servidor, abra o Agendador e confira se as duas tarefas estão como Running.
O que queremos validar
- Aplicação inicia sozinha.
- Monitor inicia sozinho.
- Pasta compartilhada fica acessível pelo monitor.
- Logs continuam sendo registrados.
- Nenhum terminal precisa ficar aberto.

Faça o teste de reinicialização e me conte se tudo voltou a funcionar. Depois podemos trabalhar em uma pequena melhoria: criar um painel de status do DebDocs para consultar se a aplicação e o monitor estão ativos, sem precisar abrir o Agendador de Tarefas.