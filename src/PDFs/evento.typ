
// Título do Evento
#set text(
  font: "New Computer Modern",
  size: 14pt
)
#align(center)[
  = "Fizz Buzz Kata"
]

#align(center)[
  #set text(
    font: "New Computer Modern",
    size: 15pt
  )
]

// Organizador

*Informações do Organizador:*

#set text(
  font: "New Computer Modern",
  size: 11pt
)
#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>
    if x == 0 or y == 0 { gray },
  inset: (right: 1.5em),
)
#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>
    if x != 0 or x == 0 { gray.lighten(30%) },
  inset: (right: 1.5em),
)

#show table.cell: it => {
  if it.x == 0 {
    set text(black.lighten(5%))
    strong(it)
  } else if it.body == [] {
    // Substitui células vazias por "N/A"
    pad(..it.inset)[_N/A_]
  } else {
    it
  }
}

#table(
  columns: 2,
  [Responsável:], [`danrley.pereira`],
  [E-mail do Responsável:], [`danrley.pereira@cs.udf.edu.br`],
  [Telefone:], [`(61) 9 8463-0170`],
)

#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>
    if x == 0 or y == 0 { blue },
  inset: (right: 1.5em),
)
#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>
    if x != 0 or x == 0 { blue.lighten(50%) },
  inset: (right: 1.5em),
)

#show table.cell: it => {
  if it.x == 0 {
    set text(black.lighten(5%))
    strong(it)
  } else if it.body == [] {
    pad(..it.inset)[_N/A_]
  } else {
    it
  }
}

#set text(
  font: "New Computer Modern",
  size: 14pt
)

// Evento

*Informações do Evento:*

#set text(
  font: "New Computer Modern",
  size: 11pt
)

#table(
  columns: 2,
  [Tipo de Evento:], [`workshop`],
  [ODS:], [`Educação de qualidade`],
  [Descrição:], [`TDD e Pair Programming para resolver o Kata`],
  [Curso:], [`71`],
  [Público Alvo:], [`['alunosUDF']`],
  [Recursos Necessários:], [`['tecnologias']`],
  [Número de Participantes Esperados:], [`12`],
  [Sala:], [`laboratorioInformática`],
  [Trilha Empreendedora:], [`Não associado a trilha empreendedora`],
  [Projeto de Extensão:], [`PIBIT - LabTech`],
  [Alunos Monitores:], [`['Gabriel', 'Valeria']`],
  [Data:],[`29/03/2025`],
  [Horário de inicio:],[`21:37`],
  [Horário final:],[`23:37`],   
)
    