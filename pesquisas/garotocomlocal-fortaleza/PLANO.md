# Plano — perfis de Fortaleza em garotocomlocal.com.br filtrados por região

Objetivo: entrar em cada sub-página de profissional listada em
<https://garotocomlocal.com.br/fortaleza/> e montar a lista dos que atendem
na **zona sul de Fortaleza**, no bairro **Aeroporto** ou no bairro **Varjota**.

## 1. Como o site está estruturado

Levantado por inspeção do HTML (sem JavaScript necessário):

| Item | Onde está | Observação |
|---|---|---|
| Lista de perfis | `/fortaleza/` — uma única página, sem paginação | ~235 links `/acompanhante-masculino/<slug>/` |
| Endereço no card | `<span itemprop="streetAddress">` (cards grandes) e `div.smallthumb-address` (cards pequenos) | Já traz o bairro na listagem |
| Página do perfil | `/acompanhante-masculino/<slug>/` | HTML estático, permitido pelo `robots.txt` |
| Endereço no perfil | `<span itemprop="streetAddress">` | Formato `"[Rua X - ]Bairro, Fortaleza - CE, Brasil"` |
| WhatsApp | `<span class="whatsapp-phone">` | |
| Cadastro | texto `Anunciante desde dd/mm/aaaa` e `Documentos verificados ✓` | |
| Texto do anúncio | `<div id="text" class="listify_widget_panel_listing_content">` | Contém idade/altura/peso em formato livre |
| Vídeo | presença de `<video` | Badge "▶️ VIDEO" na listagem |
| "Sem local" | no nome/`aria-label` (ex.: `Toni Rabão - Sem local`) | Não atende no próprio endereço |

Cerca de 1/4 dos perfis usa endereço genérico `"Fortaleza - CE, Brasil"` (sem
bairro). Para esses, a única chance de localizar é o texto do anúncio.

## 2. Etapas

1. Baixar `/fortaleza/` e extrair todos os links de perfil (dedup por URL).
2. Baixar cada perfil (4 requisições em paralelo, 250 ms de pausa, 3 retentativas,
   cache em disco em `cache/` para não rebaixar em reexecuções).
3. Extrair de cada perfil: nome, endereço, bairro, WhatsApp, data de cadastro,
   documentos verificados, vídeo, flag "sem local", idade/altura/peso, texto.
4. Derivar o bairro do endereço (`rsplit(" - ")` + corte em `", Fortaleza"`).
5. Classificar o bairro:
   - `aeroporto` / `varjota` — bairros pedidos explicitamente;
   - `sul` — bairros da Regional VI (Messejana, Cambeba, Passaré, José de Alencar,
     Cajazeiras, Edson Queiroz, Barroso, Jangurussu, Sapiranga, Cidade dos
     Funcionários, Lagoa Redonda, Curió, Guajeru, Paupina, Ancuri, etc.);
   - `sudoeste` — Regional V (Mondubim, Bom Jardim, Conjunto Ceará, Siqueira,
     Maraponga, José Walter…), listados à parte porque "sul de Fortaleza" é ambíguo;
   - `nao informado` — endereço genérico; nesse caso procura os bairros-alvo no texto.
6. Gerar `perfis_fortaleza.csv`/`.json` (todos) e `resultado.md` (filtrados),
   agrupados por bairro, com link para o perfil e WhatsApp.

## 3. Decisões e limites

- **"Sul de Fortaleza"** foi interpretado como Regional VI. A Regional V fica em
  seção separada no `resultado.md` para o usuário decidir se inclui.
- O bairro vem do endereço cadastrado pelo anunciante; o site não garante que
  ele atenda só ali (muitos atendem em motel/hotel em qualquer bairro).
- Perfis "sem local" aparecem marcados, não excluídos.
- Perfis sem bairro no endereço e sem menção no texto não podem ser classificados
  sem contato direto; ficam listados em seção própria.
- Nenhum perfil da página tinha bairro **Aeroporto** ou **Varjota** no endereço
  nem citava esses bairros no texto na data da coleta. A lista final, portanto,
  contém apenas a zona sul.

## 4. Reexecução

```bash
source .venv/bin/activate
python pesquisas/garotocomlocal-fortaleza/scrape.py            # baixa o que faltar
python pesquisas/garotocomlocal-fortaleza/scrape.py --offline  # só reprocessa o cache
```

Para forçar dados novos, apague `pesquisas/garotocomlocal-fortaleza/cache/`.
