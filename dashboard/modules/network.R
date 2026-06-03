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
        column(3, sliderInput(ns("country_top_n"), "Country map size", min = 8, max = 35, value = 18, step = 1))
      )
    ),
    br(),
    div(class = "section-grid",
      card("Research-to-Code Network", withSpinner(visNetworkOutput(ns("network_plot"), height = "620px")), class = "span-8"),
      card("Selected / Top Node Details", withSpinner(DTOutput(ns("node_detail"))), class = "span-4"),
      card("Country Collaboration Map", withSpinner(plotlyOutput(ns("country_map"), height = "560px")), caption("Curved lines show top country-pair collaborations; thicker, darker arcs mean stronger collaboration."), class = "span-8"),
      card("Top Country Collaboration Pairs", withSpinner(DTOutput(ns("country_pairs"))), class = "span-4")
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

    country_arc_points <- function(lon1, lat1, lon2, lat2, n = 36, curve = 0.16) {
      dx <- lon2 - lon1
      if (dx > 180) lon2 <- lon2 - 360
      if (dx < -180) lon2 <- lon2 + 360
      dx <- lon2 - lon1
      dy <- lat2 - lat1
      distance <- sqrt(dx^2 + dy^2)
      if (!is.finite(distance) || distance == 0) return(tibble(lon = numeric(), lat = numeric()))
      normal_lon <- -dy / distance
      normal_lat <- dx / distance
      bend <- min(20, max(3, distance * curve))
      mid_lon <- (lon1 + lon2) / 2 + normal_lon * bend
      mid_lat <- (lat1 + lat2) / 2 + normal_lat * bend
      t <- seq(0, 1, length.out = n)
      lon <- (1 - t)^2 * lon1 + 2 * (1 - t) * t * mid_lon + t^2 * lon2
      lat <- (1 - t)^2 * lat1 + 2 * (1 - t) * t * mid_lat + t^2 * lat2
      lon <- ifelse(lon > 180, lon - 360, ifelse(lon < -180, lon + 360, lon))
      tibble(lon = lon, lat = lat)
    }

    country_collaboration <- reactive({
      edges <- app_data$country_edges
      countries <- app_data$country_map
      centroids <- app_data$country_centroids
      if (!nrow(edges) || !nrow(countries) || !nrow(centroids)) return(list(nodes = tibble(), pairs = tibble(), arcs = tibble()))

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
        transmute(
          country_code = as.character(.data$country_code),
          country_name = coalesce(as.character(.data$country_name), as.character(.data$country_code)),
          country_iso3 = coalesce(as.character(.data$country_iso3), as.character(.data$country_code)),
          paper_count = as_number(.data$paper_count, 0)
        ) |>
        distinct()
      centroid_lookup <- centroids |>
        transmute(country_code = as.character(.data$country_code), lat = as_number(.data$lat, NA_real_), lon = as_number(.data$lon, NA_real_)) |>
        filter(!is.na(.data$lat), !is.na(.data$lon)) |>
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
      if (!nrow(pairs)) return(list(nodes = tibble(), pairs = tibble(), arcs = tibble()))

      strength <- bind_rows(
        pairs |> transmute(country_code = .data$source, weight = .data$weight),
        pairs |> transmute(country_code = .data$target, weight = .data$weight)
      ) |>
        group_by(.data$country_code) |>
        summarise(total_collaborations = sum(.data$weight, na.rm = TRUE), .groups = "drop") |>
        arrange(desc(.data$total_collaborations)) |>
        slice_head(n = top_n)
      country_codes <- strength$country_code
      if (!length(country_codes)) return(list(nodes = tibble(), pairs = tibble(), arcs = tibble()))

      nodes <- country_lookup |>
        filter(.data$country_code %in% country_codes) |>
        left_join(strength, by = "country_code") |>
        left_join(centroid_lookup, by = "country_code") |>
        filter(!is.na(.data$lat), !is.na(.data$lon)) |>
        mutate(
          total_collaborations = as_number(.data$total_collaborations, 0),
          marker_size = pmin(28, pmax(7, 6 + sqrt(.data$total_collaborations)))
        ) |>
        arrange(desc(.data$total_collaborations))
      country_codes <- nodes$country_code
      if (!length(country_codes)) return(list(nodes = tibble(), pairs = tibble(), arcs = tibble()))

      pairs <- pairs |>
        filter(.data$source %in% country_codes, .data$target %in% country_codes) |>
        left_join(country_lookup |> rename(source = country_code, source_name = country_name), by = "source") |>
        left_join(country_lookup |> rename(target = country_code, target_name = country_name), by = "target") |>
        left_join(centroid_lookup |> rename(source = country_code, source_lat = lat, source_lon = lon), by = "source") |>
        left_join(centroid_lookup |> rename(target = country_code, target_lat = lat, target_lon = lon), by = "target") |>
        mutate(
          source_name = coalesce(.data$source_name, .data$source),
          target_name = coalesce(.data$target_name, .data$target),
          weight_scaled = sqrt(.data$weight / max(.data$weight, na.rm = TRUE)),
          line_width = 0.7 + 5.2 * .data$weight_scaled,
          line_alpha = 0.14 + 0.48 * .data$weight_scaled
        ) |>
        filter(!is.na(.data$source_lat), !is.na(.data$source_lon), !is.na(.data$target_lat), !is.na(.data$target_lon)) |>
        arrange(desc(.data$weight), .data$source_name, .data$target_name) |>
        slice_head(n = min(90, max(28, top_n * 4)))
      if (!nrow(pairs)) return(list(nodes = nodes, pairs = tibble(), arcs = tibble()))

      arcs <- bind_rows(lapply(seq_len(nrow(pairs)), function(idx) {
        arc <- country_arc_points(pairs$source_lon[idx], pairs$source_lat[idx], pairs$target_lon[idx], pairs$target_lat[idx])
        if (!nrow(arc)) return(tibble())
        arc |>
          mutate(
            pair_id = idx,
            source_name = pairs$source_name[idx],
            target_name = pairs$target_name[idx],
            weight = pairs$weight[idx],
            line_width = pairs$line_width[idx],
            line_alpha = pairs$line_alpha[idx],
            hover = paste0(pairs$source_name[idx], " - ", pairs$target_name[idx], "<br>Collaborations: ", pairs$weight[idx])
          )
      }))
      list(nodes = nodes, pairs = pairs, arcs = arcs)
    })

    output$country_map <- renderPlotly({
      collab <- country_collaboration()
      if (!nrow(collab$nodes)) return(plotly_empty())

      p <- plot_geo() |>
        layout(
          geo = list(
            showframe = FALSE,
            showcoastlines = TRUE,
            coastlinecolor = "#94a3b8",
            showland = TRUE,
            landcolor = "#f8fafc",
            showcountries = TRUE,
            countrycolor = "#cbd5e1",
            projection = list(type = "natural earth")
          ),
          showlegend = FALSE,
          margin = list(l = 0, r = 0, t = 0, b = 0)
        )

      if (nrow(collab$arcs)) {
        for (pair_id in unique(collab$arcs$pair_id)) {
          arc <- collab$arcs |> filter(.data$pair_id == !!pair_id)
          opacity <- max(0.12, min(0.68, arc$line_alpha[1]))
          p <- p |>
            add_trace(
              data = arc,
              type = "scattergeo",
              mode = "lines",
              lon = ~lon,
              lat = ~lat,
              text = ~hover,
              hoverinfo = "text",
              line = list(width = arc$line_width[1], color = paste0("rgba(37,99,235,", round(opacity, 3), ")"))
            )
        }
      }

      p |>
        add_trace(
          data = collab$nodes,
          type = "scattergeo",
          mode = "markers+text",
          lon = ~lon,
          lat = ~lat,
          text = ~country_code,
          textposition = "top center",
          hoverinfo = "text",
          hovertext = ~paste0(country_name, "<br>Papers: ", paper_count, "<br>Country collaborations: ", total_collaborations),
          marker = list(
            size = collab$nodes$marker_size,
            color = collab$nodes$total_collaborations,
            colorscale = paper_count_colorscale,
            reversescale = FALSE,
            opacity = 0.92,
            colorbar = list(title = "Collaborations"),
            line = list(color = "#ffffff", width = 1)
          ),
          textfont = list(size = 10, color = "#0f172a")
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
