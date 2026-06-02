methods_ui <- function(id) {
  ns <- NS(id)
  div(class = "section-grid",
    card("Data Sources", tags$ul(
      tags$li("OpenAlex Works, authorships, institutions, venues, citations, topics, and open-access metadata."),
      tags$li("Official Papers With Code dumps for paper-to-repository links."),
      tags$li("GitHub REST API for public repository and contributor metadata."),
      tags$li("User-supplied venue quality CSV for A*/A/Q1 labels.")
    ), class = "span-6"),
    card("Crawl Manifest Summary", withSpinner(DTOutput(ns("manifest_table"))), class = "span-6"),
    card("Data Quality", withSpinner(DTOutput(ns("quality_table"))), class = "span-6"),
    card("Exact Search Queries", withSpinner(DTOutput(ns("query_table"))), class = "span-6"),
    card("Exports", uiOutput(ns("export_links")), class = "span-12")
  )
}

methods_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    output$manifest_table <- renderDT({
      files <- list.files(file.path(root_dir, "data", "manifests"), pattern = "\\.json$", full.names = TRUE)
      tbl <- tibble(file = basename(files), modified = file.info(files)$mtime)
      datatable(tbl, options = list(pageLength = 10), rownames = FALSE)
    })

    output$quality_table <- renderDT({
      count_type <- function(type) {
        if (!nrow(app_data$nodes) || !"node_type" %in% names(app_data$nodes)) return(0)
        nrow(app_data$nodes |> filter(node_type == type))
      }
      tbl <- tibble(
        metric = c("Papers", "Authors", "Institutions", "Countries", "Venues", "Repositories", "PWC matches", "Demo mode"),
        value = c(nrow(app_data$papers), count_type("Author"), count_type("Institution"),
                  count_type("Country"), nrow(app_data$venues), nrow(app_data$repos),
                  nrow(app_data$paper_code_links), has_demo_mode)
      )
      datatable(tbl, options = list(dom = "t"), rownames = FALSE)
    })

    output$query_table <- renderDT({
      path <- file.path(root_dir, "config", "search_queries.yaml")
      if (!file.exists(path)) return(datatable(tibble()))
      lines <- readLines(path, warn = FALSE)
      queries <- stringr::str_match(lines, "^\\s*-\\s*\"?(.*?)\"?\\s*$")[,2]
      queries <- queries[!is.na(queries) & nzchar(queries)]
      datatable(tibble(query = queries), options = list(pageLength = 12), rownames = FALSE)
    })

    output$export_links <- renderUI({
      exports <- c("nodes.csv", "edges.csv", "dashboard_kpis.csv", "dashboard_timeseries.csv", "dashboard_topic_year.csv", "dashboard_country_map.csv", "dashboard_code_gap.csv")
      tags$ul(lapply(exports, function(x) tags$li(tags$code(file.path("data/processed", x)))))
    })
  })
}
