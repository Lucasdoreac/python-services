

// Título do Evento
#set text(
  font: "New Computer Modern",
  size: 14pt
)
#align(center)[
  = "Event name"
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

    if x != 0 {gray.lighten(55%)}
    else {gray.lighten(35%)},
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

#table(
  columns: 2,
  [Responsável:], [`udff`],
  [E-mail do Responsável:], [`udff@udf.edu.br`],
  [Telefone:], [``],
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

    if x != 0 {blue.lighten(59%)}
    else {blue.lighten(45%)},
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
  [Tipo de Evento:], [``],
  [ODS:], [`None`],
  [Descrição:], [``],
  [Curso:], [``],
  [Número de Participantes Esperados:], [``],
  [Trilha Empreendedora:], [`Não associado a trilha empreendedora`],
  [Projeto de Extensão:], [`extensionProject`],
  
)



#table(
  columns: 2,
  [Público Alvo:], [`Fluminense Football Club, Gama Football Club`],
  [Recursos Necessários:], [`sdsdsdsd, Jhon Adolfo Arias Andrade`],
  [Alunos Monitores:], [`German Ezequiel Cano Recaldeeee, Jhon Adolfo Arias Andrade`],
  
)


#set text(
  font: "New Computer Modern",
  size: 14pt
)

// Evento

*Informações da Reserva do Evento:*

#set text(
  font: "New Computer Modern",
  size: 11pt
)

#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>

    if x != 0 {orange.lighten(50%)}
    else {orange.lighten(30%)},
  inset: (right: 1.5em),
)

#table(
  columns: 2,
  
  [Sala:], [``],
  [Data:],[`Sem data informada ainda`],
  [Horário de inicio:],[`Sem horário de início informado ainda`],
  [Horário final:],[`Sem horário final informado ainda`], 
  
)
    