
// Título do Evento
#set text(
  font: "New Computer Modern",
  size: 14pt
)
#align(center)[
  = "Seminário de Inovação"
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
  [Responsável:], [`gabriel`],
  [E-mail do Responsável:], [`gabriel@udf.edu.br`],
  [Telefone:], [`987654321`],
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
  [Tipo de Evento:], [`Seminário`],
  [ODS:], [`Indústria, Inovação e Infraestrutura`],
  [Descrição:], [`Um evento sobre inovação e tecnologia.`],
  [Curso:], [`Engenharia de Software`],
  [Público Alvo:], [`Estudantes e profissionais`],
  [Recursos Necessários:], [`Projetor, Computadores`],
  [Número de Participantes Esperados:], [`150`],
  [Sala:], [`Auditório Principal`],
  [Trilha Empreendedora:], [`Inovação Tecnológica`],
  [Projeto de Extensão:], [`Projeto de Pesquisa`],
  [Alunos Monitores:], [`João, Maria`],
  [Data:],[`30/09/2025`],
  [Horário de inicio:],[`19:00`],
  [Horário final:],[`21:00`],   
)
    