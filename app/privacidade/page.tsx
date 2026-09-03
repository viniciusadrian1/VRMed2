import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Logo } from "@/components/layout/Logo";

export const metadata: Metadata = {
  title: "Política de Privacidade",
  description:
    "Como o VRmed coleta e trata dados anônimos de uso para fins de pesquisa em Iniciação Científica.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-dvh">
      <header className="border-b border-border">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-5">
          <Logo />
          <Link
            href="/"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Início
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-12">
        <h1 className="font-serif text-4xl font-medium tracking-tight">
          Política de Privacidade
        </h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Última atualização: 3 de setembro de 2026
        </p>
        <p className="mt-3 text-muted-foreground">
          O VRmed é um projeto de Iniciação Científica em educação médica. Esta
          página descreve, de forma transparente, quais dados a aplicação coleta
          e como eles são tratados, em conformidade com a Lei Geral de Proteção
          de Dados (LGPD).
        </p>

        <div className="mt-10 flex flex-col gap-8 text-sm leading-relaxed">
          <section>
            <h2 className="font-serif text-xl font-medium">
              Dados que coletamos
            </h2>
            <p className="mt-2 text-muted-foreground">
              Mediante o seu consentimento explícito, registramos{" "}
              <strong className="font-medium text-foreground">
                eventos de uso anônimos
              </strong>{" "}
              para gerar evidências quantitativas sobre o aprendizado imersivo.
              Entre eles:
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              <li>quais órgãos são visualizados e por quanto tempo;</li>
              <li>quais ferramentas são usadas (cortes, raio-X, camadas);</li>
              <li>início e conclusão de quizzes, com a pontuação obtida;</li>
              <li>uso do modo de comparação e da realidade virtual;</li>
              <li>
                avaliações (positivas ou negativas) das respostas do tutor.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-serif text-xl font-medium">
              Dados que NÃO coletamos
            </h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              <li>
                Nenhuma informação pessoal — nome, e-mail, matrícula ou
                identificadores diretos.
              </li>
              <li>
                O texto das perguntas feitas ao tutor não é registrado na
                telemetria: enviamos apenas um código de verificação (hash)
                irreversível e uma categoria temática.
              </li>
              <li>
                Utilizamos o Umami, uma solução de analytics que prioriza a
                privacidade, sem cookies nem rastreamento entre sites.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-serif text-xl font-medium">Consentimento</h2>
            <p className="mt-2 text-muted-foreground">
              Nenhum dado de uso é enviado antes de você aceitar explicitamente
              a coleta, por meio do banner exibido no primeiro acesso. É
              possível recusar a qualquer momento — a aplicação continua
              plenamente funcional sem a telemetria.
            </p>
          </section>

          <section>
            <h2 className="font-serif text-xl font-medium">
              Avaliação das respostas do tutor
            </h2>
            <p className="mt-2 text-muted-foreground">
              Ao avaliar uma resposta do tutor de IA (com 👍/👎 ou um
              comentário), o conteúdo daquela pergunta e resposta específica é
              armazenado para validação por especialistas — uma etapa essencial
              da pesquisa. Esses registros não contêm sua identificação.
            </p>
          </section>

          <section>
            <h2 className="font-serif text-xl font-medium">
              Dados armazenados no seu navegador
            </h2>
            <p className="mt-2 text-muted-foreground">
              Sessões de estudo, anotações e o histórico de conversas ficam
              salvos apenas no seu navegador (armazenamento local). As mensagens
              que você envia ao tutor de IA são transmitidas ao nosso servidor
              somente para gerar a resposta e não são guardadas nele. Você pode
              remover tudo limpando os dados do site.
            </p>
          </section>

          <section>
            <h2 className="font-serif text-xl font-medium">
              Serviços de terceiros
            </h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              <li>
                <strong className="font-medium text-foreground">OpenAI</strong>{" "}
                — as perguntas ao tutor são processadas pela API da OpenAI, nos
                Estados Unidos, exclusivamente para gerar a resposta. Não inclua
                dados pessoais nas perguntas.
              </li>
              <li>
                <strong className="font-medium text-foreground">Umami</strong> —
                analytics sem cookies nem rastreamento entre sites, carregado só
                depois do seu consentimento no banner.
              </li>
              <li>
                <strong className="font-medium text-foreground">Spotify</strong>{" "}
                — opcional, na Sala de Estudos: o login usa apenas escopos de
                reprodução e playlists, os tokens ficam só no seu navegador e
                &quot;Desconectar Spotify&quot; os apaga. Nada passa pelo
                servidor do VRmed.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-serif text-xl font-medium">Contato</h2>
            {/* TODO(dono): incluir e-mail do grupo e, se houver, nº do CAAE */}
            <p className="mt-2 text-muted-foreground">
              Dúvidas sobre o tratamento de dados podem ser encaminhadas à
              equipe responsável pelo projeto de Iniciação Científica do VRmed.
            </p>
          </section>
        </div>

        <div className="mt-12 border-t border-border pt-6">
          <Link
            href="/"
            className="text-sm font-medium text-primary underline underline-offset-2"
          >
            Voltar à página inicial
          </Link>
        </div>
      </main>
    </div>
  );
}
