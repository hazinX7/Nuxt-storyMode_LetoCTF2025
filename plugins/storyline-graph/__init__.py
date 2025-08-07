from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from CTFd.models import db, Challenges, Solves, Users, Teams
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, get_current_team
from CTFd.plugins import register_plugin_assets_directory, override_template, bypass_csrf_protection
from CTFd.plugins import register_plugin_asset
from CTFd.utils import get_config, set_config
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import json
from pathlib import Path


class StorylineChallenge(db.Model):
    __tablename__ = 'storyline_challenges'

    id = Column(Integer, primary_key=True)
    challenge_id = Column(Integer, ForeignKey('challenges.id', ondelete='CASCADE'), nullable=False, unique=True)
    predecessor_id = Column(Integer, ForeignKey('challenges.id', ondelete='SET NULL'), nullable=True)
    max_lifetime = Column(Integer, nullable=True)

    challenge = relationship("Challenges", foreign_keys=[challenge_id])
    predecessor = relationship("Challenges", foreign_keys=[predecessor_id])

class SolutionDescription(db.Model):
    __tablename__ = 'solution_descriptions'

    id = Column(Integer, primary_key=True)
    solve_id = Column(Integer, ForeignKey('solves.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    challenge_id = Column(Integer, ForeignKey('challenges.id', ondelete='CASCADE'), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    solve = relationship("Solves")
    team = relationship("Teams")
    challenge = relationship("Challenges")


def get_unlocked_challenges_for_team(team_id):
    if not team_id:
        return []

    solved_challenges = db.session.query(Solves.challenge_id, Solves.date).filter_by(team_id=team_id).all()
    solved_ids = [solve.challenge_id for solve in solved_challenges]
    solved_dict = {solve.challenge_id: solve.date for solve in solved_challenges}

    storyline_challenges = StorylineChallenge.query.all()
    storyline_dict = {sc.challenge_id: sc for sc in storyline_challenges}

    unlocked_ids = set()

    for challenge in Challenges.query.all():
        if challenge.id in storyline_dict:
            sc = storyline_dict[challenge.id]

            if not sc.predecessor_id:
                unlocked_ids.add(challenge.id)
            elif sc.predecessor_id in solved_ids:
                predecessor_solve_time = solved_dict[sc.predecessor_id]

                if sc.max_lifetime:
                    time_limit = timedelta(minutes=sc.max_lifetime)
                    if datetime.utcnow() - predecessor_solve_time <= time_limit:
                        unlocked_ids.add(challenge.id)
                else:
                    unlocked_ids.add(challenge.id)
        else:
            unlocked_ids.add(challenge.id)

    return list(unlocked_ids)

def get_graph_data(team_id=None):
    challenges = Challenges.query.all()
    storyline_challenges = StorylineChallenge.query.all()

    storyline_dict = {sc.challenge_id: sc for sc in storyline_challenges}
    challenge_dict = {c.id: c for c in challenges}

    nodes = []
    edges = []

    solved_ids = set()
    unlocked_ids = set()
    
    if team_id:
        solved_challenges = Solves.query.filter_by(team_id=team_id).all()
        solved_ids = {solve.challenge_id for solve in solved_challenges}
        unlocked_ids = set(get_unlocked_challenges_for_team(team_id))
    else:
        unlocked_ids = {c.id for c in challenges}

    visible_challenge_ids = set()
    if team_id:
        visible_challenge_ids = solved_ids.copy()
        
        for challenge_id in unlocked_ids:
            if challenge_id in storyline_dict:
                sc = storyline_dict[challenge_id]
                if (sc.predecessor_id is None or 
                    sc.predecessor_id in solved_ids or 
                    sc.predecessor_id in unlocked_ids):
                    visible_challenge_ids.add(challenge_id)
            else:
                visible_challenge_ids.add(challenge_id)
    else:
        visible_challenge_ids = {c.id for c in challenges}

    added_node_ids = set()
    
    for challenge in challenges:
        if challenge.id not in visible_challenge_ids:
            continue
            

        if challenge.id in added_node_ids:
            continue
            
        status = 'locked'
        if team_id:
            if challenge.id in solved_ids:
                status = 'solved'
            elif challenge.id in unlocked_ids:
                status = 'unlocked'
        else:
            status = 'unlocked'

        node = {
            'id': challenge.id,
            'label': challenge.name,
            'status': status,
            'category': challenge.category,
            'value': challenge.value
        }

        if challenge.id in storyline_dict:
            sc = storyline_dict[challenge.id]
            if sc.max_lifetime:
                node['max_lifetime'] = sc.max_lifetime

        nodes.append(node)
        added_node_ids.add(challenge.id)


    added_edges = set()
    
    for sc in storyline_challenges:
        if (sc.predecessor_id and 
            sc.predecessor_id in visible_challenge_ids and 
            sc.challenge_id in visible_challenge_ids):
            
            edge_key = (sc.predecessor_id, sc.challenge_id)
            
            if edge_key in added_edges:
                continue
                
            edges.append({
                'from': sc.predecessor_id,
                'to': sc.challenge_id,
                'has_timer': sc.max_lifetime is not None
            })
            added_edges.add(edge_key)


    if team_id:
        print(f" * Debug for team {team_id}:")
        print(f"   - Total challenges: {len(challenges)}")
        print(f"   - Solved challenges: {len(solved_ids)} - {list(solved_ids)}")
        print(f"   - Unlocked challenges: {len(unlocked_ids)} - {list(unlocked_ids)}")
        print(f"   - Visible challenges: {len(visible_challenge_ids)} - {list(visible_challenge_ids)}")
        print(f"   - Storyline challenges: {len(storyline_challenges)}")
        for sc in storyline_challenges:
            challenge_name = challenge_dict.get(sc.challenge_id, {}).name if sc.challenge_id in challenge_dict else f"ID:{sc.challenge_id}"
            predecessor_name = challenge_dict.get(sc.predecessor_id, {}).name if sc.predecessor_id and sc.predecessor_id in challenge_dict else f"ID:{sc.predecessor_id}"
            print(f"     {challenge_name} <- {predecessor_name if sc.predecessor_id else 'ROOT'}")

    return {'nodes': nodes, 'edges': edges}


storyline_bp = Blueprint('storyline', __name__, template_folder='templates', static_folder='assets')

@storyline_bp.route('/admin/storyline-graph')
@admins_only
def admin_graph():
    graph_data = get_graph_data()
    return render_template('admin_graph.html', graph_data=json.dumps(graph_data))

@storyline_bp.route('/admin/storyline-manage')
@admins_only
def admin_storyline_manage():
    return render_template('admin_storyline.html')

@storyline_bp.route('/storyline-graph')
@authed_only
def player_graph():
    team = get_current_team()
    team_id = team.id if team else None
    graph_data = get_graph_data(team_id)
    return render_template('player_graph.html', graph_data=json.dumps(graph_data))

@storyline_bp.route('/api/storyline/graph')
@authed_only
def api_graph():
    team = get_current_team()
    team_id = team.id if team else None
    graph_data = get_graph_data(team_id)
    return jsonify(graph_data)

@storyline_bp.route('/api/admin/storyline/graph')
@admins_only
def api_admin_graph():
    graph_data = get_graph_data()
    return jsonify(graph_data)

@storyline_bp.route('/api/admin/storyline/challenge/<int:challenge_id>', methods=['POST'])
@admins_only
@bypass_csrf_protection
def update_storyline_challenge(challenge_id):
    data = request.get_json()


    sc = StorylineChallenge.query.filter_by(challenge_id=challenge_id).first()
    if not sc:
        sc = StorylineChallenge(challenge_id=challenge_id)
        db.session.add(sc)


    predecessor_id = data.get('predecessor_id')
    sc.predecessor_id = predecessor_id if predecessor_id else None

    max_lifetime = data.get('max_lifetime')
    sc.max_lifetime = max_lifetime if max_lifetime else None

    db.session.commit()

    return jsonify({'success': True})

@storyline_bp.route('/api/admin/storyline/challenges')
@admins_only
def api_admin_storyline_challenges():
    storyline_challenges = StorylineChallenge.query.all()
    result = {}
    for sc in storyline_challenges:
        result[sc.challenge_id] = {
            'predecessor_id': sc.predecessor_id,
            'max_lifetime': sc.max_lifetime
        }
    return jsonify(result)

@storyline_bp.route('/api/storyline/solution-description', methods=['POST'])
@authed_only
def submit_solution_description():
    data = request.get_json()
    team = get_current_team()

    if not team:
        return jsonify({'error': 'No team found'}), 400

    challenge_id = data.get('challenge_id')
    description = data.get('description', '').strip()

    if not description:
        return jsonify({'error': 'Description is required'}), 400


    solve = Solves.query.filter_by(
        team_id=team.id,
        challenge_id=challenge_id
    ).order_by(Solves.date.desc()).first()

    if not solve:
        return jsonify({'error': 'No solve found for this challenge'}), 400


    existing = SolutionDescription.query.filter_by(
        solve_id=solve.id,
        team_id=team.id,
        challenge_id=challenge_id
    ).first()

    if existing:
        existing.description = description
    else:
        solution_desc = SolutionDescription(
            solve_id=solve.id,
            team_id=team.id,
            challenge_id=challenge_id,
            description=description
        )
        db.session.add(solution_desc)

    db.session.commit()
    return jsonify({'success': True})

@storyline_bp.route('/api/admin/storyline/competition-format', methods=['GET'])
@admins_only
def get_competition_format():
    format_value = get_config('competition_format') or 'jeopardy'
    return jsonify({
        'success': True,
        'data': {
            'format': format_value
        }
    })

@storyline_bp.route('/api/admin/storyline/competition-format', methods=['POST'])
@admins_only
@bypass_csrf_protection
def set_competition_format():
    data = request.get_json()
    format_value = data.get('format', 'jeopardy')
    

    if format_value not in ['jeopardy', 'hack_quest']:
        return jsonify({
            'success': False,
            'message': 'Invalid format. Must be "jeopardy" or "hack_quest"'
        }), 400
    

    set_config('competition_format', format_value)
    
    return jsonify({
        'success': True,
        'message': f'Competition format set to {format_value}'
    })

def cleanup_storyline_data(challenge_id):
    try:

        StorylineChallenge.query.filter_by(challenge_id=challenge_id).delete()
        StorylineChallenge.query.filter_by(predecessor_id=challenge_id).update({'predecessor_id': None})
        

        SolutionDescription.query.filter_by(challenge_id=challenge_id).delete()
        
        db.session.commit()
        print(f" * Cleaned up storyline data for challenge {challenge_id}")
    except Exception as e:
        print(f" * Error cleaning up storyline data for challenge {challenge_id}: {e}")
        db.session.rollback()

def get_challenges_url():
    format_value = get_config('competition_format') or 'jeopardy'
    if format_value == 'hack_quest':
        return '/storyline-graph'
    else:
        return '/challenges'

def load(app):


    with app.app_context():
        db.create_all()
        

        try:

            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            if 'sqlite' in database_url.lower():

                print(" * SQLite detected - CASCADE handled by ORM")
            else:

                print(" * Checking foreign key constraints for storyline tables...")
                

                inspector = db.inspect(db.engine)
                tables = inspector.get_table_names()
                
                if 'storyline_challenges' in tables:

                    try:
                        db.session.execute(db.text("""
                            ALTER TABLE storyline_challenges 
                            DROP CONSTRAINT IF EXISTS storyline_challenges_ibfk_1
                        """))
                        db.session.execute(db.text("""
                            ALTER TABLE storyline_challenges 
                            DROP CONSTRAINT IF EXISTS storyline_challenges_ibfk_2
                        """))
                        db.session.execute(db.text("""
                            ALTER TABLE storyline_challenges 
                            ADD CONSTRAINT storyline_challenges_challenge_id_fk 
                            FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE CASCADE
                        """))
                        db.session.execute(db.text("""
                            ALTER TABLE storyline_challenges 
                            ADD CONSTRAINT storyline_challenges_predecessor_id_fk 
                            FOREIGN KEY (predecessor_id) REFERENCES challenges(id) ON DELETE SET NULL
                        """))
                        db.session.commit()
                        print(" * Updated storyline_challenges constraints")
                    except Exception as e:
                        db.session.rollback()
                        print(f" * Constraints already exist or update not needed: {e}")
                        
                if 'solution_descriptions' in tables:
                    try:
                        db.session.execute(db.text("""
                            ALTER TABLE solution_descriptions 
                            DROP CONSTRAINT IF EXISTS solution_descriptions_ibfk_1
                        """))
                        db.session.execute(db.text("""
                            ALTER TABLE solution_descriptions 
                            DROP CONSTRAINT IF EXISTS solution_descriptions_ibfk_2
                        """))
                        db.session.execute(db.text("""
                            ALTER TABLE solution_descriptions 
                            DROP CONSTRAINT IF EXISTS solution_descriptions_ibfk_3
                        """))
                        db.session.execute(db.text("""
                            ALTER TABLE solution_descriptions 
                            ADD CONSTRAINT solution_descriptions_solve_id_fk 
                            FOREIGN KEY (solve_id) REFERENCES solves(id) ON DELETE CASCADE
                        """))
                        db.session.execute(db.text("""
                            ALTER TABLE solution_descriptions 
                            ADD CONSTRAINT solution_descriptions_team_id_fk 
                            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
                        """))
                        db.session.execute(db.text("""
                            ALTER TABLE solution_descriptions 
                            ADD CONSTRAINT solution_descriptions_challenge_id_fk 
                            FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE CASCADE
                        """))
                        db.session.commit()
                        print(" * Updated solution_descriptions constraints")
                    except Exception as e:
                        db.session.rollback()
                        print(f" * Constraints already exist or update not needed: {e}")
        except Exception as e:
            print(f" * Could not update constraints automatically: {e}")
            print(" * Run migration_fix_cascade.py manually if deletion errors persist")


    app.register_blueprint(storyline_bp)
    

    @app.context_processor
    def inject_challenges_url():
        return dict(get_challenges_url=get_challenges_url)
    

    @app.before_request
    def cleanup_storyline_on_delete():
        from flask import request
        if (request.method == 'DELETE' and 
            request.endpoint == 'api.challenges_challenge' and
            'challenge_id' in request.view_args):
            
            challenge_id = request.view_args.get('challenge_id')
            if challenge_id:

                try:
                    StorylineChallenge.query.filter_by(challenge_id=challenge_id).delete()
                    StorylineChallenge.query.filter_by(predecessor_id=challenge_id).update({'predecessor_id': None})
                    SolutionDescription.query.filter_by(challenge_id=challenge_id).delete()
                    db.session.commit()
                    print(f" * Pre-cleaned storyline data for challenge {challenge_id}")
                except Exception as e:
                    print(f" * Pre-cleanup error for challenge {challenge_id}: {e}")
                    db.session.rollback()


    dir_path = Path(__file__).parent
    register_plugin_assets_directory(
        app,
        base_path=f'/plugins/storyline-graph/assets/',

    )


    template_path = dir_path / 'templates' / 'challenge_form_override.html'
    if template_path.exists():
        override_template('admin/challenges.html', open(template_path).read())


    js_path = dir_path / 'assets' / 'storyline.js'
    if js_path.exists():
        register_plugin_asset(app, asset_path='/plugins/storyline-graph/assets/storyline.js')


    def custom_challenges_view():
        from flask import render_template
        from CTFd.utils.user import get_current_user
        from CTFd.utils.modes import get_model

        user = get_current_user()
        team = get_current_team()

        if team:
            unlocked_challenge_ids = get_unlocked_challenges_for_team(team.id)
            challenges = Challenges.query.filter(Challenges.id.in_(unlocked_challenge_ids)).all()
        else:
            challenges = Challenges.query.all()

        return render_template('challenges.html', challenges=challenges)



