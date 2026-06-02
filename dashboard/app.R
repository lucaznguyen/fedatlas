source("global.R", local = TRUE)
source("modules/overview.R", local = TRUE)
source("modules/collaboration.R", local = TRUE)
source("modules/topics.R", local = TRUE)
source("modules/network.R", local = TRUE)
source("modules/code_gap.R", local = TRUE)
source("modules/repos.R", local = TRUE)
source("modules/venues.R", local = TRUE)
source("modules/methods.R", local = TRUE)

theme <- bs_theme(
  version = 5,
  bg = "#f8fafc",
  fg = "#0f172a",
  primary = "#2563eb",
  base_font = "Averta, Inter, Avenir, 'Helvetica Neue', Arial, sans-serif"
)

ui <- fluidPage(
  theme = theme,
  tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
  ),
  div(class = "app-shell",
    div(class = "hero-band",
      div(class = "hero-copy",
        tags$span(class = "eyebrow", "Federated Learning Research Atlas"),
        h1("FedAtlas"),
        p("Mapping the Global Research-to-Code Ecosystem of Federated Learning"),
        if (has_demo_mode) tags$span(class = "demo-pill", "Demo mode active") else NULL
      ),
      div(class = "hero-meta",
        div(strong(metric_value("Papers")), span("papers")),
        div(strong(metric_value("GitHub Repos")), span("repos")),
        div(strong(metric_value("Research-to-Code Score")), span("code adoption"))
      )
    ),
    div(class = "dashboard-grid",
      tags$aside(class = "filter-rail",
        h2("Filters"),
        sliderInput("year_range", "Year range", min = min(available_years), max = max(available_years), value = range(available_years), sep = ""),
        pickerInput("topic_group", "Topic group", choices = safe_choices(app_data$papers$topic_group), selected = safe_choices(app_data$papers$topic_group), multiple = TRUE, options = list(`actions-box` = TRUE, size = 8)),
        pickerInput("venue_quality", "Venue quality", choices = c("A*", "A", "Q1", "Unknown", "Not_Target"), selected = c("A*", "A", "Q1"), multiple = TRUE, options = list(`actions-box` = TRUE)),
        radioGroupButtons("has_code", "Code", choices = c("All", "Has GitHub", "No GitHub"), selected = "All", justified = TRUE, size = "sm"),
        numericInput("min_citations", "Minimum citations", value = 0, min = 0, step = 1),
        numericInput("min_stars", "Minimum GitHub stars", value = 0, min = 0, step = 1),
        sliderInput("top_n", "Top N", min = 5, max = 100, value = 25, step = 5),
        textInput("search_box", "Search", placeholder = "Paper, venue, topic, repo"),
        hr(),
        download_button("download_filtered_papers", "Export filtered papers")
      ),
      tags$main(class = "main-stage",
        tabsetPanel(id = "main_tabs", type = "tabs",
          tabPanel("Overview", overview_ui("overview")),
          tabPanel("Global Collaboration", collaboration_ui("collaboration")),
          tabPanel("Topic Evolution", topics_ui("topics")),
          tabPanel("Network Explorer", network_ui("network")),
          tabPanel("Research-to-Code Gap", code_gap_ui("codegap")),
          tabPanel("Repositories & Contributors", repos_ui("repos")),
          tabPanel("Venues & Quality", venues_ui("venues")),
          tabPanel("Data & Methods", methods_ui("methods"))
        )
      )
    )
  )
)

server <- function(input, output, session) {
  filtered_papers <- reactive({
    papers <- filter_dataset(app_data$papers, input)
    if (!nrow(papers)) return(papers)
    if (input$has_code != "All" && nrow(app_data$paper_code_links)) {
      ids <- unique(app_data$paper_code_links$work_id)
      if (input$has_code == "Has GitHub") papers <- papers |> filter(.data$work_id %in% ids)
      if (input$has_code == "No GitHub") papers <- papers |> filter(!.data$work_id %in% ids)
    }
    papers
  })

  output$download_filtered_papers <- downloadHandler(
    filename = function() paste0("fedatlas_filtered_papers_", Sys.Date(), ".csv"),
    content = function(file) readr::write_csv(filtered_papers(), file)
  )

  overview_server("overview", filtered_papers)
  collaboration_server("collaboration", filtered_papers)
  topics_server("topics", filtered_papers)
  network_server("network", filtered_papers)
  code_gap_server("codegap", filtered_papers)
  repos_server("repos", filtered_papers)
  venues_server("venues", filtered_papers)
  methods_server("methods", filtered_papers)
}

shinyApp(ui, server)
