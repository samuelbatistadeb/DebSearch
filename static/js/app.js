
"use strict";

/* =========================================
   CONFIGURAÇÕES
========================================= */

const LIMITE = 15;

let paginaAtual = 1;
let totalPaginas = 0;
let csrfToken = null;

/* =========================================
   ELEMENTOS DO HTML
========================================= */

// Autenticação
const loginScreen = document.getElementById("loginScreen");
const catalogApp = document.getElementById("catalogApp");

const loginForm = document.getElementById("loginForm");
const loginUsuario = document.getElementById("loginUsuario");
const loginSenha = document.getElementById("loginSenha");
const loginError = document.getElementById("loginError");
const loginButton = document.getElementById("loginButton");

const logoutButton = document.getElementById("logoutButton");
const currentUser = document.getElementById("currentUser");

// Catálogo
const campoPesquisa = document.getElementById("searchInput");
const botaoPesquisa = document.getElementById("searchButton");
const conteudo = document.getElementById("content");


/* =========================================
   INICIALIZAÇÃO
========================================= */

document.addEventListener("DOMContentLoaded", inicializar);

loginForm.addEventListener("submit", realizarLogin);

logoutButton.addEventListener("click", realizarLogout);

campoPesquisa.addEventListener("keydown", function(event) {

    if (event.key === "Enter") {
        pesquisar(1);
    }

});


async function inicializar() {

    try {

        await obterTokenCSRF();

        const resposta = await fetch("/me", {
            method: "GET",
            credentials: "same-origin"
        });

        if (!resposta.ok) {
            throw new Error("Não foi possível verificar a sessão.");
        }

        const dados = await resposta.json();

        if (dados.autenticado) {

            exibirCatalogo(dados.usuario);

        } else {

            exibirLogin();

        }

    } catch (erro) {

        console.error("Erro ao verificar autenticação:", erro);

        exibirLogin(
            "Não foi possível verificar a sessão. Confira sua conexão e tente novamente."
        );

    }
}


/* =========================================
   CONTROLE DE TELAS
========================================= */

function exibirLogin(mensagem = "") {

    catalogApp.hidden = true;
    loginScreen.hidden = false;

    loginError.textContent = mensagem;
    loginError.hidden = !mensagem;

    loginSenha.value = "";

    loginUsuario.focus();
}


function exibirCatalogo(usuario) {

    loginScreen.hidden = true;
    catalogApp.hidden = false;

    loginError.hidden = true;

    // Aceita os formatos mais comuns do objeto de usuário.
    const nome = typeof usuario === "string"
        ? usuario
        : (
            usuario?.usuario ||
            usuario?.nome ||
            usuario?.username ||
            usuario?.login ||
            "Usuário"
        );

    currentUser.textContent = nome;
}


/* =========================================
   LOGIN
========================================= */

async function realizarLogin(event) {

    event.preventDefault();

    const usuario = loginUsuario.value.trim();
    const senha = loginSenha.value;

    if (!usuario || !senha) {

        loginError.textContent = "Informe seu usuário e sua senha.";
        loginError.hidden = false;

        return;
    }

    loginButton.disabled = true;
    loginButton.textContent = "Entrando...";

    loginError.hidden = true;

    try {

        const resposta = await fetch("/login", {

            method: "POST",

            credentials: "same-origin",

            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": csrfToken
            },

            body: JSON.stringify({
                usuario: usuario,
                senha: senha
            })

        });

        const dados = await resposta.json();

        if (!resposta.ok) {

            throw new Error(
                dados.detail || "Não foi possível realizar o login."
            );

        }

        // O backend criou uma nova sessão após o login.
        // Precisamos obter o token CSRF dessa nova sessão.
        await obterTokenCSRF();

        exibirCatalogo(dados.usuario);

        loginForm.reset();

    } catch (erro) {

        console.error("Erro no login:", erro);

        loginError.textContent =
            erro.message || "Erro ao realizar login.";

        loginError.hidden = false;

    } finally {

        loginButton.disabled = false;
        loginButton.textContent = "Entrar";

    }
}


/* =========================================
   LOGOUT
========================================= */

async function realizarLogout() {

    logoutButton.disabled = true;
    logoutButton.textContent = "Saindo...";

    try {

        const resposta = await fetch("/logout", {

            method: "POST",

            credentials: "same-origin",

            headers: {
                "X-CSRF-Token": csrfToken
            }

        });

        if (!resposta.ok) {

            throw new Error("Não foi possível encerrar a sessão.");

        }

        exibirLogin();

    } catch (erro) {

        console.error("Erro ao encerrar sessão:", erro);

        alert(
            "Não foi possível encerrar a sessão. Tente novamente."
        );

    } finally {

        logoutButton.disabled = false;
        logoutButton.textContent = "Sair";

    }
}


/* =========================================
   FUNÇÕES AUXILIARES
========================================= */

function escaparHTML(valor) {

    return String(valor ?? "").replace(/[&<>"']/g, function(caractere) {

        const mapa = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        };

        return mapa[caractere];
    });
}


function formatarTamanho(bytes) {

    if (!bytes || bytes <= 0) return "0 KB";

    if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + " KB";
    }

    if (bytes < 1024 * 1024 * 1024) {
        return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    }

    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
}


function formatarData(valor) {

    if (!valor) return "—";

    const data = typeof valor === "number"
        ? new Date(valor * 1000)
        : new Date(valor);

    if (isNaN(data.getTime())) return "—";

    return data.toLocaleString("pt-BR");
}


function mostrarEstado(titulo, mensagem, icone = "⌕") {

    conteudo.innerHTML = `
        <div class="state">
            <div class="state-icon">${escaparHTML(icone)}</div>
            <h3>${escaparHTML(titulo)}</h3>
            <p>${escaparHTML(mensagem)}</p>
        </div>
    `;
}

/* =========================================
   PROTEÇÃO CSRF
========================================= */

async function obterTokenCSRF() {

    const resposta = await fetch("/csrf-token", {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store"
    });

    if (!resposta.ok) {
        throw new Error("Não foi possível obter o token de segurança.");
    }

    const dados = await resposta.json();

    if (!dados.csrf_token) {
        throw new Error("Token de segurança inválido.");
    }

    csrfToken = dados.csrf_token;

    return csrfToken;
}

/* =========================================
   PESQUISA
========================================= */

async function pesquisar(pagina = 1) {

    const termo = campoPesquisa.value.trim();

    if (!termo) {

        mostrarEstado(
            "Digite um termo para pesquisar",
            "Informe o nome ou parte do nome do documento."
        );

        document.getElementById("resultCount").textContent =
            "Aguardando pesquisa.";

        document.getElementById("pagination").style.display = "none";

        return;
    }

    paginaAtual = pagina;

    botaoPesquisa.disabled = true;
    botaoPesquisa.textContent = "Pesquisando...";

    document.getElementById("pagination").style.display = "none";

    document.getElementById("resultCount").textContent =
        "Consultando catálogo...";

    conteudo.innerHTML = `
        <div class="state">
            <div class="spinner"></div>
            <p style="margin-top: 16px;">Pesquisando documentos...</p>
        </div>
    `;

    try {

        const parametros = new URLSearchParams({
            q: termo,
            pagina: paginaAtual,
            limite: LIMITE
        });

        const resposta = await fetch(
            `/pesquisar?${parametros.toString()}`,
            {
                credentials: "same-origin"
            }
        );

        // Sessão expirada ou inválida.
        if (resposta.status === 401) {

            exibirLogin(
                "Sua sessão expirou. Entre novamente para continuar."
            );

            return;
        }

        if (!resposta.ok) {
            throw new Error("Falha ao consultar o catálogo.");
        }

        const dados = await resposta.json();

        totalPaginas = Math.ceil(dados.total / LIMITE);

        document.getElementById("resultCount").innerHTML =
            `<strong>${dados.total.toLocaleString("pt-BR")}</strong> documento(s) encontrado(s)`;

        if (!dados.resultados || dados.resultados.length === 0) {

            mostrarEstado(
                "Nenhum documento encontrado",
                "Tente pesquisar utilizando outro termo."
            );

            return;
        }

        renderizarResultados(dados.resultados);

        atualizarPaginacao(dados.total);

    } catch (erro) {

        console.error(erro);

        mostrarEstado(
            "Não foi possível realizar a pesquisa",
            "Verifique se o servidor está funcionando e tente novamente.",
            "!"
        );

        document.getElementById("resultCount").textContent =
            "Erro na pesquisa.";

    } finally {

        botaoPesquisa.disabled = false;
        botaoPesquisa.textContent = "Pesquisar";

    }
}


/* =========================================
   RESULTADOS
========================================= */

function renderizarResultados(resultados) {

    let linhas = "";

    resultados.forEach(function(documento) {

        const nome = escaparHTML(documento.nome);

        const extensao = escaparHTML(
            (documento.extensao || "arquivo").replace(".", "")
        );

        const data = escaparHTML(formatarData(documento.modificado_em));

        const tamanho = escaparHTML(
            formatarTamanho(documento.tamanho_bytes)
        );

        const id = encodeURIComponent(documento.id);

        const caminho = String(documento.caminho ?? "");

        linhas += `
            <tr>

                <td>
                    <div class="document-name">

                        <div class="file-icon">▤</div>

                        <div class="file-name" title="${nome}">
                            ${nome}
                        </div>

                    </div>
                </td>

                <td>${data}</td>

                <td>
                    <span class="extension">${extensao}</span>
                </td>

                <td>${tamanho}</td>

                <td>
                    <div class="actions">

                        <a
                            class="action-button"
                            href="/arquivo/${id}"
                            title="Baixar documento"
                        >
                            ↓ Baixar
                        </a>

                        <button
                            class="action-button"
                            onclick="copiarCaminho(this)"
                            data-path="${escaparHTML(caminho)}"
                            title="Copiar caminho"
                        >
                            ⧉ Caminho
                        </button>

                    </div>
                </td>

            </tr>
        `;
    });

    conteudo.innerHTML = `
        <div class="table-wrapper">

            <table>

                <thead>
                    <tr>
                        <th>Documento</th>
                        <th>Modificado em</th>
                        <th>Formato</th>
                        <th>Tamanho</th>
                        <th>Ações</th>
                    </tr>
                </thead>

                <tbody>
                    ${linhas}
                </tbody>

            </table>

        </div>
    `;
}


/* =========================================
   CÓPIA DE CAMINHO
========================================= */

async function copiarCaminho(botao) {

    const caminho = botao.getAttribute("data-path");

    try {

        await navigator.clipboard.writeText(caminho);

        const textoOriginal = botao.innerHTML;

        botao.innerHTML = "✓ Copiado";

        setTimeout(function() {
            botao.innerHTML = textoOriginal;
        }, 1500);

    } catch (erro) {

        alert("Não foi possível copiar o caminho.");

    }
}


/* =========================================
   PAGINAÇÃO
========================================= */

function atualizarPaginacao(total) {

    const paginacao = document.getElementById("pagination");

    if (totalPaginas <= 1) {

        paginacao.style.display = "none";

        return;
    }

    paginacao.style.display = "flex";

    const inicio = ((paginaAtual - 1) * LIMITE) + 1;

    const fim = Math.min(paginaAtual * LIMITE, total);

    document.getElementById("paginationInfo").textContent =
        `Exibindo ${inicio}–${fim} de ${total.toLocaleString("pt-BR")} documentos`;

    document.getElementById("currentPage").textContent =
        `Página ${paginaAtual} de ${totalPaginas}`;

    document.getElementById("previousButton").disabled =
        paginaAtual <= 1;

    document.getElementById("nextButton").disabled =
        paginaAtual >= totalPaginas;
}
