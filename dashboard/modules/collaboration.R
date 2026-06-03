collaboration_ui <- function(id) {
  ns <- NS(id)
  div(class = "section-grid",
    card("Global Collaboration Map", withSpinner(plotlyOutput(ns("world_map"), height = "460px")), caption("Country shading encodes paper count; darker countries contribute more papers. Country names come from OpenAlex institution affiliations."), class = "span-8"),
    card("Bridge Countries", withSpinner(DTOutput(ns("country_rank"))), class = "span-4"),
    card("Country-Pair Collaboration", withSpinner(DTOutput(ns("country_pairs"))), class = "span-12")
  )
}

collaboration_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    output$world_map <- renderPlotly({
      cm <- app_data$country_map
      if (!nrow(cm)) return(plotly_empty())
      if (!"country_iso3" %in% names(cm)) return(plotly_empty())
      plot_geo(cm) |>
        add_trace(
          type = "choropleth",
          locations = ~country_iso3,
          locationmode = "ISO-3",
          z = ~paper_count,
          text = ~paste0(country_name, "<br>Papers: ", paper_count, "<br>Citations: ", citations),
          colorscale = "Blues",
          marker = list(line = list(color = "#ffffff", width = 0.4))
        ) |>
        layout(geo = list(showframe = FALSE, showcoastlines = TRUE, projection = list(type = "natural earth")))
    })

    output$country_rank <- renderDT({
      nodes <- app_data$nodes
      if (!nrow(nodes)) return(datatable(tibble()))
      nodes |> filter(node_type == "Country") |> transmute(
        Country = display_label,
        Degree = degree,
        `Bridge score` = round(bridge_score, 3),
        PageRank = round(pagerank, 5)
      ) |> arrange(desc(`Bridge score`)) |> datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })

    output$country_pairs <- renderDT({
      edges <- app_data$country_edges
      if (!nrow(edges)) return(datatable(tibble()))
      edges |> arrange(desc(weight)) |> datatable(options = list(pageLength = 15, scrollX = TRUE), rownames = FALSE)
    })
  })
}
