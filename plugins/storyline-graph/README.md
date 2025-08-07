# CTFd Storyline Graph Plugin

A CTFd plugin that transforms challenges into a cohesive storyline represented as a directed graph. Each challenge becomes a node in the story, with dependencies and optional time limits creating an engaging narrative flow.

## Features

### Core Functionality
- **Challenge Dependencies**: Set prerequisite challenges that must be solved before unlocking new ones
- **Time-Based Challenges**: Optional time limits for side quests and bonus challenges
- **Solution Write-ups**: Teams must provide solution descriptions after solving challenges
- **Visual Graph Interface**: Beautiful interactive graph showing challenge relationships

### Admin Features
- **Graph Management**: Visual interface for setting up challenge dependencies
- **Time Limit Configuration**: Set time windows for time-sensitive challenges
- **Progress Monitoring**: View team progress through the storyline
- **Solution Review**: Access all team solution descriptions for evaluation

### Player Features
- **Interactive Map**: Visual representation of available, solved, and locked challenges
- **Progress Tracking**: Clear indication of storyline completion
- **Intuitive Navigation**: Click challenges to navigate directly to them
- **Status Indicators**: Color-coded challenges based on availability

## Installation

1. Copy the `storyline-graph` folder to your CTFd `plugins` directory
2. Restart CTFd
3. The plugin will automatically create the necessary database tables

## Usage

### For Administrators

1. **Access Management Interface**: Go to Admin Panel → Plugins → Storyline Graph
2. **Set Dependencies**: 
   - Select a challenge
   - Choose its prerequisite challenge (or leave empty for root challenges)
   - Optionally set a time limit in minutes
3. **View Graph**: Visit `/admin/storyline-graph` to see the complete challenge graph

### For Players

1. **View Storyline**: Click "Storyline" in the navigation bar
2. **Navigate Challenges**: Click on available (yellow) challenges to solve them
3. **Track Progress**: Monitor your advancement through the story
4. **Submit Solutions**: After solving, provide a brief description of your approach

## Database Schema

### storyline_challenges
- `id`: Primary key
- `challenge_id`: Foreign key to challenges table
- `predecessor_id`: Foreign key to prerequisite challenge (nullable)
- `max_lifetime`: Time limit in minutes (nullable)

### solution_descriptions
- `id`: Primary key
- `solve_id`: Foreign key to solves table
- `team_id`: Foreign key to teams table
- `challenge_id`: Foreign key to challenges table
- `description`: Team's solution description
- `created_at`: Timestamp

## API Endpoints

### Player Endpoints
- `GET /storyline-graph`: Storyline visualization page
- `GET /api/storyline/graph`: Graph data for current team
- `POST /api/storyline/solution-description`: Submit solution description

### Admin Endpoints
- `GET /admin/storyline-graph`: Admin graph visualization
- `GET /admin/storyline-manage`: Challenge management interface
- `GET /api/admin/storyline/graph`: Complete graph data
- `GET /api/admin/storyline/challenges`: Storyline configurations
- `POST /api/storyline/challenge/<id>`: Update challenge configuration

## Graph Visualization

The plugin uses [Vis.js Network](https://visjs.github.io/vis-network/docs/network/) for interactive graph visualization:

- **Green nodes**: Solved challenges
- **Yellow nodes**: Available challenges
- **Red nodes**: Locked challenges
- **Diamond shapes**: Time-limited challenges
- **Dashed edges**: Time-sensitive dependencies

## Configuration Options

### Challenge Dependencies
- Set any challenge as a prerequisite for another
- Create branching storylines with multiple paths
- Prevent circular dependencies automatically

### Time Limits
- Set time windows for side quests
- Branches close if not completed within the time limit
- Time starts counting from when prerequisite is solved

## Development

### File Structure
```
storyline-graph/
├── __init__.py              # Main plugin code
├── config.json              # Plugin configuration
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── assets/
│   ├── storyline.js        # Frontend JavaScript
│   └── storyline.css       # Plugin styles
└── templates/
    ├── admin_graph.html    # Admin graph view
    ├── admin_storyline.html # Admin management interface
    └── player_graph.html   # Player storyline view
```

### Key Functions
- `get_unlocked_challenges_for_team()`: Determines available challenges
- `get_graph_data()`: Generates visualization data
- `load()`: Plugin entry point and initialization

## Troubleshooting

### Common Issues
1. **Plugin not appearing**: Ensure CTFd has been restarted after installation
2. **Database errors**: Check that CTFd has write permissions to the database
3. **Graph not loading**: Verify that vis.js CDN is accessible

### Debug Information
- Admin graph view includes debug data display
- Check browser console for JavaScript errors
- Verify API endpoints are responding correctly

## License

This plugin follows the same license as CTFd (Apache 2.0).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and feature requests, please use the CTFd GitHub repository or contact the plugin maintainer.
