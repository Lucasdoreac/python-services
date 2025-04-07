
// Título do Evento
#set text(
  font: "New Computer Modern",
  size: 14pt
)
#align(center)[
  = "Testando Aplicação"
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
  [Responsável:], [`gabrielOF`],
  [E-mail do Responsável:], [`gabrielOF@udf.edu.br`],
  [Telefone:], [`(61) 9 8922-0022`],
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
  [Tipo de Evento:], [`exam`],
  [ODS:], [`Vida terrestre`],
  [Descrição:], [`Testar Descrição do evento/ Objetivos,Descrição do evento/ Objetivos`],
  [Curso:], [`31`],
  [Público Alvo:], [`['alunosUDF']`],
  [Recursos Necessários:], [`['tecnologias']`],
  [Número de Participantes Esperados:], [`10`],
  [Sala:], [`auditorio`],
  [Trilha Empreendedora:], [`Não associado a trilha empreendedora`],
  [Projeto de Extensão:], [`Não`],
  [Alunos Monitores:], [`Sem alunos monitores`],
  [Data:],[`02/04/2025`],
  [Horário de inicio:],[`01:41`],
  [Horário final:],[`03:41`],   
)
    