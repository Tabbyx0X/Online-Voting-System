"""
Sample Data Generator for Online Voting System
Run this script to populate the database with test data
Usage: python generate_test_data.py
"""

from app import app, db, Admin, Election, Candidate, Voter, Vote
from datetime import datetime, timedelta
import random

def generate_test_data():
    with app.app_context():
        print("=" * 50)
        print("Generating Test Data for Online Voting System")
        print("=" * 50)
        
        # Clear existing data (optional - comment out if you want to keep existing data)
        # Vote.query.delete()
        # Candidate.query.delete()
        # Election.query.delete()
        # Voter.query.delete()
        # db.session.commit()
        # print("✓ Cleared existing data")
        
        # Create sample elections
        elections_data = [
            {
                'title': 'Student Council President Election 2024',
                'description': 'Annual election for student council president position',
                'start_date': datetime.now() - timedelta(days=2),
                'end_date': datetime.now() + timedelta(days=5),
                'status': 'active'
            },
            {
                'title': 'Class Representative Election',
                'description': 'Elect class representatives for the academic year',
                'start_date': datetime.now() + timedelta(days=10),
                'end_date': datetime.now() + timedelta(days=15),
                'status': 'upcoming'
            },
            {
                'title': 'Sports Committee Head Election 2024',
                'description': 'Choose the head of sports committee',
                'start_date': datetime.now() - timedelta(days=30),
                'end_date': datetime.now() - timedelta(days=25),
                'status': 'completed'
            }
        ]
        
        elections = []
        for data in elections_data:
            election = Election(**data)
            election.update_status()
            db.session.add(election)
            elections.append(election)
        
        db.session.commit()
        print(f"✓ Created {len(elections)} elections")
        
        # Create sample candidates
        candidates_data = [
            # For Student Council President
            [
                {
                    'name': 'John Anderson',
                    'party': 'Student First Party',
                    'description': 'Experienced leader with a vision to improve campus life. Committed to student welfare and academic excellence.',
                    'photo_url': 'https://ui-avatars.com/api/?name=John+Anderson&size=200&background=0D8ABC&color=fff'
                },
                {
                    'name': 'Sarah Mitchell',
                    'party': 'Progressive Student Alliance',
                    'description': 'Innovative thinker focused on technology integration and sustainable campus development.',
                    'photo_url': 'https://ui-avatars.com/api/?name=Sarah+Mitchell&size=200&background=F59E0B&color=fff'
                },
                {
                    'name': 'Michael Chen',
                    'party': 'Independent',
                    'description': 'Independent candidate with fresh perspectives on student representation and campus activities.',
                    'photo_url': 'https://ui-avatars.com/api/?name=Michael+Chen&size=200&background=10B981&color=fff'
                },
                {
                    'name': 'Emily Rodriguez',
                    'party': 'Unity Party',
                    'description': 'Passionate about diversity, inclusion, and creating opportunities for all students.',
                    'photo_url': 'https://ui-avatars.com/api/?name=Emily+Rodriguez&size=200&background=EF4444&color=fff'
                }
            ],
            # For Class Representative
            [
                {
                    'name': 'David Brown',
                    'party': 'Class Unity',
                    'description': 'Dedicated to bridging the gap between students and faculty.',
                    'photo_url': 'https://ui-avatars.com/api/?name=David+Brown&size=200&background=8B5CF6&color=fff'
                },
                {
                    'name': 'Lisa Wang',
                    'party': 'Student Voice',
                    'description': 'Advocate for better communication and class engagement.',
                    'photo_url': 'https://ui-avatars.com/api/?name=Lisa+Wang&size=200&background=EC4899&color=fff'
                },
                {
                    'name': 'Robert Taylor',
                    'party': 'Independent',
                    'description': 'Focused on academic support and peer mentoring programs.',
                    'photo_url': 'https://ui-avatars.com/api/?name=Robert+Taylor&size=200&background=06B6D4&color=fff'
                }
            ],
            # For Sports Committee Head
            [
                {
                    'name': 'James Wilson',
                    'party': 'Sports Excellence',
                    'description': 'Former athlete committed to promoting sports culture on campus.',
                    'photo_url': 'https://ui-avatars.com/api/?name=James+Wilson&size=200&background=0EA5E9&color=fff'
                },
                {
                    'name': 'Maria Garcia',
                    'party': 'Fitness First',
                    'description': 'Advocate for inclusive sports programs and wellness initiatives.',
                    'photo_url': 'https://ui-avatars.com/api/?name=Maria+Garcia&size=200&background=22C55E&color=fff'
                },
                {
                    'name': 'Alex Johnson',
                    'party': 'Active Campus',
                    'description': 'Experienced organizer focused on tournaments.',
                    'photo_url': 'https://ui-avatars.com/api/?name=Alex+Johnson&size=200&background=F97316&color=fff'
                }
            ]
        ]
        
        all_candidates = []
        for i, election in enumerate(elections):
            for candidate_data in candidates_data[i]:
                candidate = Candidate(**candidate_data, election_id=election.id)
                db.session.add(candidate)
                all_candidates.append(candidate)
        
        db.session.commit()
        print(f"✓ Created {len(all_candidates)} candidates")
        
        # Create sample voters
        voters_data = [
            {'voter_id': 'V001', 'name': 'Alice Johnson', 'email': 'alice@example.com', 'password': 'password123'},
            {'voter_id': 'V002', 'name': 'Bob Smith', 'email': 'bob@example.com', 'password': 'password123'},
            {'voter_id': 'V003', 'name': 'Charlie Davis', 'email': 'charlie@example.com', 'password': 'password123'},
            {'voter_id': 'V004', 'name': 'Diana Evans', 'email': 'diana@example.com', 'password': 'password123'},
            {'voter_id': 'V005', 'name': 'Edward Miller', 'email': 'edward@example.com', 'password': 'password123'},
            {'voter_id': 'V006', 'name': 'Fiona White', 'email': 'fiona@example.com', 'password': 'password123'},
            {'voter_id': 'V007', 'name': 'George Harris', 'email': 'george@example.com', 'password': 'password123'},
            {'voter_id': 'V008', 'name': 'Hannah Lee', 'email': 'hannah@example.com', 'password': 'password123'},
            {'voter_id': 'V009', 'name': 'Ian Martinez', 'email': 'ian@example.com', 'password': 'password123'},
            {'voter_id': 'V010', 'name': 'Julia Thompson', 'email': 'julia@example.com', 'password': 'password123'},
        ]
        
        voters = []
        for data in voters_data:
            # Check if voter already exists
            existing = Voter.query.filter_by(voter_id=data['voter_id']).first()
            if not existing:
                voter = Voter(voter_id=data['voter_id'], name=data['name'], email=data['email'])
                voter.set_password(data['password'])
                db.session.add(voter)
                voters.append(voter)
        
        db.session.commit()
        print(f"✓ Created {len(voters)} voters")
        
        # Generate sample votes for active and completed elections
        vote_count = 0
        for election in elections:
            if election.status in ['active', 'completed']:
                candidates = Candidate.query.filter_by(election_id=election.id).all()
                # Randomly assign votes (70% of voters)
                voting_voters = random.sample(voters, k=min(7, len(voters)))
                
                for voter in voting_voters:
                    # Check if already voted
                    if not voter.has_voted(election.id):
                        candidate = random.choice(candidates)
                        vote = Vote(voter_id=voter.id, election_id=election.id, candidate_id=candidate.id)
                        db.session.add(vote)
                        vote_count += 1
        
        db.session.commit()
        print(f"✓ Created {vote_count} sample votes")
        
        print("\n" + "=" * 50)
        print("Test Data Generation Complete!")
        print("=" * 50)
        print("\nTest Voter Credentials:")
        print("------------------------")
        print("Voter ID: V001 - V010")
        print("Password: password123")
        print("\nAdmin Credentials:")
        print("------------------")
        print("Username: admin")
        print("Password: admin123")
        print("\n" + "=" * 50)

if __name__ == '__main__':
    try:
        generate_test_data()
        print("\n✓ Success! You can now log in and test the system.")
    except Exception as e:
        print(f"\n✗ Error generating test data: {e}")
        print("Make sure the database is set up and the application is configured correctly.")
