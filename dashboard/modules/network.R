network_ui <- function(id) {
  ns <- NS(id)
  node_choices <- c("Paper", "Topic", "GitHubRepo", "Author", "Institution", "Venue", "Contributor")
  relation_choices <- setdiff(safe_choices(app_data$edges$relation), c("collaborates_with", "located_in"))
  default_relations <- intersect(c("has_topic", "has_implementation"), relation_choices)
  if (!length(default_relations)) default_relations <- relation_choices
  tagList(
    div(class = "panel-card",
      fluidRow(
        column(3, pickerInput(ns("node_types"), "Research-code node types", choices = node_choices, selected = c("Paper", "Topic", "GitHubRepo"), multiple = TRUE, options = list(`actions-box` = TRUE))),
        column(3, pickerInput(ns("edge_types"), "Research-code edge types", choices = relation_choices, selected = default_relations, multiple = TRUE, options = list(`actions-box` = TRUE))),
        column(3, sliderInput(ns("network_top_n"), "Network nodes", min = 25, max = 800, value = 150, step = 25)),
        column(3, sliderInput(ns("country_top_n"), "Country matrix size", min = 8, max = 35, value = 18, step = 1))
      )
    ),
    br(),
    div(class = "section-grid",
      card("Research-to-Code Network", withSpinner(visNetworkOutput(ns("network_plot"), height = "620px")), class = "span-8"),
      card("Selected / Top Node Details", withSpinner(DTOutput(ns("node_detail"))), class = "span-4"),
      card("Country Collaboration Matrix", withSpinner(plotlyOutput(ns("country_matrix"), height = "520px")), caption("Cell color encodes summed country-pair collaboration count; darker blue means stronger collaboration."), class = "span-8"),
      card("Top Country Collaboration Pairs", withSpinner(DTOutput(ns("country_pairs"))), class = "span-4"),
      card("Research-Code Community Summary", withSpinner(DTOutput(ns("community_summary"))), class = "span-12")
    )
  )
}

network_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    visible_network <- reactive({
      nodes <- app_data$nodes
      edges <- app_data$edges
      if (!nrow(nodes) || !nrow(edges)) return(list(nodes = tibble(), edges = tibble()))

      selected_node_types <- input$node_types
      if (!length(selected_node_types)) selected_node_types <- c("Paper", "Topic", "GitHubRepo")
      selected_edge_types <- input$edge_types
      if (!length(selected_edge_types)) selected_edge_types <- intersect(c("has_topic", "has_implementation"), safe_choices(edges$relation))
      if (!length(selected_edge_types)) selected_edge_types <- safe_choices(edges$relation)
      top_n <- suppressWarnings(as.integer(input$network_top_n))
      if (is.na(top_n) || top_n < 25) top_n <- 150

      papers <- filtered_papers()
      paper_ids <- if (nrow(papers) && "work_id" %in% names(papers)) unique(papers$work_id) else character()
      edges <- edges |>
        mutate(weight = pmax(1, as_number(.data$weight, 1)), directed = as_flag(.data$directed)) |>
        filter(
          .data$relation %in% selected_edge_types,
          .data$source_type %in% selected_node_types,
          .data$target_type %in% selected_node_types
        )
      if (length(paper_ids) && "Paper" %in% selected_node_types) {
        edges <- edges |>
          filter((.data$source_type != "Paper" | .data$source %in% paper_ids) &
                   (.data$target_type != "Paper" | .data$target %in% paper_ids))
      }
      if (!nrow(edges)) return(list(nodes = tibble(), edges = tibble()))

      endpoint_degree <- bind_rows(
        edges |> transmute(node_id = .data$source, incident_weight = .data$weight),
        edges |> transmute(node_id = .data$target, incident_weight = .data$weight)
      ) |>
        group_by(.data$node_id) |>
        summarise(network_degree = n(), network_weight = sum(.data$incident_weight, na.rm = TRUE), .groups = "drop")

      nodes <- nodes |>
        filter(.data$node_type %in% selected_node_types, .data$node_id %in% endpoint_degree$node_id) |>
        left_join(endpoint_degree, by = "node_id") |>
        mutate(
          size_metric = pmax(1, as_number(.data$size_metric, 1)),
          weighted_degree = as_number(.data$weighted_degree, 0),
          pagerank = as_number(.data$pagerank, 0),
          network_degree = as_number(.data$network_degree, 0),
          network_weight = as_number(.data$network_weight, 0),
          network_score = .data$network_weight + .data$weighted_degree + log1p(.data$size_metric)
        )
      if (!nrow(nodes)) return(list(nodes = tibble(), edges = tibble()))

      quotas <- tibble(node_type = selected_node_types) |>
        mutate(quota = case_when(
          .data$node_type == "Paper" ~ max(10, floor(top_n * 0.40)),
          .data$node_type == "Topic" ~ max(8, floor(top_n * 0.18)),
          .data$node_type == "GitHubRepo" ~ max(10, floor(top_n * 0.22)),
          .data$node_type == "Country" ~ max(8, floor(top_n * 0.16)),
          TRUE ~ max(8, floor(top_n / max(1, length(selected_node_types))))
        ))
      seed_nodes <- nodes |>
        left_join(quotas, by = "node_type") |>
        group_by(.data$node_type) |>
        arrange(desc(.data$network_score), desc(.data$size_metric), .by_group = TRUE) |>
        mutate(type_rank = row_number()) |>
        ungroup() |>
        filter(.data$type_rank <= .data$quota)

      relation_priority <- c("has_implementation", "has_topic", "published_in", "affiliated_with_paper", "writes", "contributes_to", "cites", "coauthors")
      priority_edges <- edges |>
        mutate(priority = match(.data$relation, relation_priority), priority = coalesce(.data$priority, length(relation_priority) + 1)) |>
        arrange(.data$priority, desc(.data$weight)) |>
        group_by(.data$relation) |>
        slice_head(n = max(20, floor(top_n * 0.35))) |>
        ungroup()

      selected_ids <- unique(c(seed_nodes$node_id, priority_edges$source, priority_edges$target))
      selected_edges <- edges |>
        filter(.data$source %in% selected_ids, .data$target %in% selected_ids) |>
        mutate(priority = match(.data$relation, relation_priority), priority = coalesce(.data$priority, length(relation_priority) + 1)) |>
        arrange(.data$priority, desc(.data$weight)) |>
        slice_head(n = max(150, top_n * 4))
      if (!nrow(selected_edges)) {
        selected_edges <- priority_edges |> slice_head(n = max(50, top_n * 2))
      }

      final_ids <- unique(c(selected_edges$source, selected_edges$target))
      list(nodes = nodes |> filter(.data$node_id %in% final_ids), edges = selected_edges)
    })

    output$network_plot <- renderVisNetwork({
      net <- visible_network()
      if (!nrow(net$nodes)) return(visNetwork(data.frame(id = "empty", label = "No network data"), data.frame()))
      max_size <- max(net$nodes$size_metric, na.rm = TRUE)
      if (!is.finite(max_size) || max_size <= 0) max_size <- 1
      vnodes <- net$nodes |> transmute(
        id = node_id,
        label = ifelse(node_type == "Paper", str_trunc(coalesce(display_label, label, node_id), 34), str_trunc(coalesce(display_label, label, node_id), 28)),
        group = node_type,
        value = 8 + 24 * sqrt(pmax(1, size_metric) / max_size),
        title = paste0(
          "<b>", node_type, "</b><br>",
          coalesce(display_label, label, node_id),
          "<br>Visible degree: ", round(network_degree, 0),
          "<br>Weighted degree: ", round(weighted_degree, 1)
        )
      )
      vedges <- net$edges |> transmute(
        from = source,
        to = target,
        value = pmin(6, pmax(1, sqrt(as_number(weight, 1)))),
        title = relation,
        arrows = ifelse(directed, "to", ""),
        dashes = relation %in% c("coauthors")
      )
      visNetwork(vnodes, vedges) |>
        visGroups(groupname = "Paper", shape = "dot", color = list(background = "#93c5fd", border = "#2563eb")) |>
        visGroups(groupname = "Topic", shape = "diamond", color = list(background = "#fde68a", border = "#d97706")) |>
        visGroups(groupname = "Country", shape = "triangle", color = list(background = "#bae6fd", border = "#0284c7")) |>
        visGroups(groupname = "GitHubRepo", shape = "box", color = list(background = "#bbf7d0", border = "#16a34a")) |>
        visOptions(highlightNearest = list(enabled = TRUE, degree = 1), nodesIdSelection = TRUE) |>
        visLegend() |>
        visInteraction(navigationButtons = TRUE) |>
        visPhysics(stabilization = TRUE, solver = "forceAtlas2Based")
    })

    output$node_detail <- renderDT({
      net <- visible_network()
      if (!nrow(net$nodes)) return(empty_dt("No connected nodes match the active network filters."))
      net$nodes |> arrange(desc(network_score)) |> select(node_type, display_label, year, topic, venue_quality, network_degree, weighted_degree, pagerank, bridge_score, url) |> slice_head(n = 25) |>
        datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })

    output$community_summary <- renderDT({
      net <- visible_network()
      if (!nrow(net$nodes)) return(empty_dt("No connected nodes match the active network filters."))
      net$nodes |> count(community, node_type, sort = TRUE) |> datatable(options = list(pageLength = 12, scrollX = TRUE), rownames = FALSE)
    })

    country_collaboration <- reactive({
      edges <- app_data$country_edges
      countries <- app_data$country_map
      if (!nrow(edges) || !nrow(countries)) return(list(matrix = NULL, pairs = tibble()))

      papers <- filtered_papers()
      if (nrow(papers) && "publication_year" %in% names(papers)) {
        active_years <- unique(as.integer(as_number(papers$publication_year, NA_real_)))
        active_years <- active_years[!is.na(active_years)]
        if (length(active_years) && "year" %in% names(edges)) {
          edges <- edges |> filter(as.integer(as_number(.data$year, NA_real_)) %in% active_years)
        }
      }

      top_n <- suppressWarnings(as.integer(input$country_top_n))
      if (is.na(top_n) || top_n < 8) top_n <- 18
      country_lookup <- countries |>
        transmute(country_code = as.character(.data$country_code), country_name = coalesce(as.character(.data$country_name), as.character(.data$country_code))) |>
        distinct()

      pairs <- edges |>
        mutate(
          source = as.character(.data$source),
          target = as.character(.data$target),
          weight = as_number(.data$weight, 0)
        ) |>
        filter(nzchar(.data$source), nzchar(.data$target), .data$source != .data$target, .data$weight > 0) |>
        group_by(.data$source, .data$target) |>
        summarise(weight = sum(.data$weight, na.rm = TRUE), .groups = "drop")
      if (!nrow(pairs)) return(list(matrix = NULL, pairs = tibble()))

      strength <- bind_rows(
        pairs |> transmute(country_code = .data$source, weight = .data$weight),
        pairs |> transmute(country_code = .data$target, weight = .data$weight)
      ) |>
        group_by(.data$country_code) |>
        summarise(total_collaborations = sum(.data$weight, na.rm = TRUE), .groups = "drop") |>
        arrange(desc(.data$total_collaborations)) |>
        slice_head(n = top_n)
      country_codes <- strength$country_code
      if (!length(country_codes)) return(list(matrix = NULL, pairs = tibble()))

      pairs <- pairs |>
        filter(.data$source %in% country_codes, .data$target %in% country_codes) |>
        left_join(country_lookup |> rename(source = country_code, source_name = country_name), by = "source") |>
        left_join(country_lookup |> rename(target = country_code, target_name = country_name), by = "target") |>
        mutate(
          source_name = coalesce(.data$source_name, .data$source),
          target_name = coalesce(.data$target_name, .data$target)
        ) |>
        arrange(desc(.data$weight), .data$source_name, .data$target_name)
      if (!nrow(pairs)) return(list(matrix = NULL, pairs = tibble()))

      labels <- country_lookup |>
        filter(.data$country_code %in% country_codes) |>
        right_join(tibble(country_code = country_codes), by = "country_code") |>
        mutate(country_name = coalesce(.data$country_name, .data$country_code)) |>
        pull(country_name)
      z <- matrix(0, nrow = length(country_codes), ncol = length(country_codes))
      for (idx in seq_len(nrow(pairs))) {
        i <- match(pairs$source[idx], country_codes)
        j <- match(pairs$target[idx], country_codes)
        if (!is.na(i) && !is.na(j)) {
          z[i, j] <- z[i, j] + pairs$weight[idx]
          z[j, i] <- z[j, i] + pairs$weight[idx]
        }
      }
      diag(z) <- NA_real_
      hover_base <- outer(labels, labels, paste, sep = " - ")
      hover <- matrix(paste0(hover_base, "<br>Collaborations: ", z), nrow = nrow(z), ncol = ncol(z))
      list(matrix = list(labels = labels, z = z, hover = hover), pairs = pairs)
    })

    output$country_matrix <- renderPlotly({
      collab <- country_collaboration()
      if (is.null(collab$matrix) || !length(collab$matrix$labels)) return(plotly_empty())
      row_order <- rev(seq_along(collab$matrix$labels))
      plot_ly(
        x = collab$matrix$labels,
        y = rev(collab$matrix$labels),
        z = collab$matrix$z[row_order, , drop = FALSE],
        text = collab$matrix$hover[row_order, , drop = FALSE],
        hoverinfo = "text",
        type = "heatmap",
        colorscale = paper_count_colorscale,
        reversescale = FALSE,
        colorbar = list(title = "Collaborations")
      ) |>
        layout(
          xaxis = list(title = "", tickangle = 45),
          yaxis = list(title = ""),
          margin = list(l = 120, b = 110)
        )
    })

    output$country_pairs <- renderDT({
      collab <- country_collaboration()
      pairs <- collab$pairs
      if (!nrow(pairs)) return(empty_dt("No country collaboration pairs match the active filters."))
      pairs |>
        transmute(
          `Source country` = .data$source_name,
          `Target country` = .data$target_name,
          Collaborations = .data$weight
        ) |>
        slice_head(n = 50) |>
        datatable(options = list(pageLength = 12, scrollX = TRUE), rownames = FALSE)
    })
  })
}
