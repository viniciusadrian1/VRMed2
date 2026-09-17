/**
 * Entrar e sair de uma sessão WebXR pelos botões do app, sem deixar sessão
 * viva sem dono nem pedidos sobrepostos.
 *
 * POR QUE ISTO EXISTE (tarja "rodando em segundo plano" no Quest Browser)
 *
 * O Quest Browser mostra uma faixa nativa com Retomar/Sair quando exibe a
 * página 2D e considera que ainda há uma sessão imersiva viva — por exemplo,
 * depois do botão Meta. Essa faixa não é do app (nenhum elemento do VRmed tem
 * esse texto) e a página não recebe os cliques nela. Os caminhos em que o app
 * podia deixar o navegador nesse estado sem ninguém para atender eram:
 * navegar com a sessão ainda viva (o hub da Sala), a cena 3D desmontar com a
 * sessão pausada, e pedir uma sessão nova por cima de uma que existe. As duas
 * funções abaixo fecham esses caminhos. Diagnóstico completo em
 * docs/CONTEXTO.md ("Tarja branca ao sair do VR/AR").
 */

interface SessaoEncerravel {
  end(): Promise<void>;
}

/** Sessões com `end()` já pedido: um segundo clique em "Sair" não repete. */
const encerrando = new WeakSet<SessaoEncerravel>();

/**
 * Encerra a sessão imersiva e SÓ DEPOIS navega. O `end()` do navegador só
 * resolve depois que ele sai do modo imersivo; navegar antes deixava a
 * derrubada da sessão para o descarte do documento.
 */
export function sairENavegar(
  sessao: SessaoEncerravel | null | undefined,
  destino: string,
  navegar: (url: string) => void = (url) => window.location.assign(url),
  rotaAtual: () => string = () => window.location.pathname,
): void {
  const ir = () => {
    // Já no destino (sair dentro do próprio visualizador): recarregar a cena
    // 3D inteira seria trabalho à toa.
    if (rotaAtual() !== destino) navegar(destino);
  };
  if (!sessao) return ir();
  if (encerrando.has(sessao)) return;
  encerrando.add(sessao);
  sessao.end().then(ir, ir);
}

interface StoreComSessao {
  getState(): { session?: SessaoEncerravel | null };
}

let pedidoEmAndamento: Promise<unknown> | null = null;

/**
 * Pede a sessão imersiva sem sobrepor pedidos.
 *
 * - Clique duplo em "Entrar em VR" devolve o mesmo pedido, em vez de um
 *   segundo `requestSession` que o navegador rejeita.
 * - Com uma sessão ainda viva (pausada pelo botão Meta, a página 2D fica
 *   clicável), encerra essa primeiro e só então pede a nova: pedir por cima
 *   só falha com InvalidStateError e mantém a sessão velha pendurada.
 */
export function entrarNoXR<T>(
  store: StoreComSessao,
  entrar: () => Promise<T>,
): Promise<T> {
  if (pedidoEmAndamento) return pedidoEmAndamento as Promise<T>;
  const pedido = (async () => {
    const viva = store.getState().session;
    if (viva) await viva.end().catch(() => {});
    return entrar();
  })();
  pedidoEmAndamento = pedido;
  const liberar = () => {
    if (pedidoEmAndamento === pedido) pedidoEmAndamento = null;
  };
  pedido.then(liberar, liberar);
  return pedido;
}
