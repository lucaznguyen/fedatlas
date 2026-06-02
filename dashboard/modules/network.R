network_ui <- function(id) {
  ns <- NS(id)
  tagList(
    div(class = "panel-card",
      fluidRow(
        column(4, pickerInput(ns("node_types"), "Node types", choices = c("Paper", "Author", "Institution", "Country", "Topic", "Venue", "GitHubRepo", "Contributor"), selected = c("Paper", "Topic", "Country", "GitHubRepo"), multiple = TRUE, options = list(`actions-box` = TRUE))),
        column(4, pickerInput(ns("edge_types"), "Edge types", choices = safe_choices(app_data$edges$relation), selected = safe_choices(app_data$edges$relation), multiple = TRUE, options = list(`actions-box` = TRUE))),
        column(4, sliderInput(ns("network_top_n"), "Network nodes", min = 25, max = 800, value = 150, step = 25))
      )
    ),
    br(),
    div(class = "section-grid",
      card("Heterogeneous Network", withSpinner(visNetworkOutput(ns("network_plot"), height = "620px")), class = "span-8"),
      card("Selected / Top Node Details", withSpinner(DTOutput(ns("node_detail"))), class = "span-4"),
      card("Community Summary", withSpinner(DTOutput(ns("community_summary"))), class = "span-12")
    )
  )
}

network_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    visible_network <- reactive({
      nodes <- app_data$nodes
      edges <- app_data$edges
      if (!nrow(nodes) || !nrow(edges)) return(list(nodes = tibble(), edges = tibble()))
      nodes <- nodes |> filter(node_type %in% input$node_types) |> arrange(desc(coalesce(pagerank, 0)), desc(coalesce(size_metric, 0))) |> slice_head(n = input$network_top_n)
      edges <- edges |> filter(source %in% nodes$node_id, target %in% nodes$node_id, relation %in% input$edge_types)
      list(nodes = nodes, edges = edges)
    })

    output$network_plot <- renderVisNetwork({
      net <- visible_network()
      if (!nrow(net$nodes)) return(visNetwork(data.frame(id = "empty", label = "No network data"), data.frame()))
      vnodes <- net$nodes |> transmute(
        id = node_id,
        label = str_trunc(coalesce(display_label, label, node_id), 42),
        group = node_type,
        value = pmax(1, coalesce(size_metric, degree, 1)),
        title = paste0("<b>", node_type, "</b><br>", coalesce(display_label, label, node_id), "<br>PageRank: ", round(coalesce(pagerank, 0), 5))
      )
      vedges <- net$edges |> transmute(from = source, to = target, value = pmax(1, coalesce(weight, 1)), title = relation, arrows = ifelse(directed, "to", ""))
      visNetwork(vnodes, vedges) |>
        visOptions(highlightNearest = list(enabled = TRUE, degree = 1), nodesIdSelection = TRUE) |>
        visLegend() |>
        visPhysics(stabilization = TRUE, solver = "forceAtlas2Based")
    })

    output$node_detail <- renderDT({
      net <- visible_network()
      if (!nrow(net$nodes)) return(datatable(tibble()))
      net$nodes |> arrange(desc(pagerank)) |> select(node_type, display_label, year, topic, venue_quality, degree, betweenness, pagerank, bridge_score, url) |> slice_head(n = 25) |>
        datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })

    output$community_summary <- renderDT({
      net <- visible_network()
      if (!nrow(net$nodes)) return(datatable(tibble()))
      net$nodes |> count(community, node_type, sort = TRUE) |> datatable(options = list(pageLength = 12, scrollX = TRUE), rownames = FALSE)
    })
  })
}
