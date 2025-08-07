// Storyline Graph Plugin JavaScript

// Handle solution description submission after solving a challenge
function showSolutionDescriptionModal(challengeId, challengeName) {
    const modalHtml = `
        <div class="modal fade" id="solutionModal" tabindex="-1" role="dialog">
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Solution Description</h5>
                        <button type="button" class="close" data-dismiss="modal">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <p>Please provide a brief description of how you solved <strong>${challengeName}</strong>:</p>
                        <textarea id="solution-description" class="form-control" rows="4" 
                                  placeholder="Describe your approach, tools used, key insights, etc."></textarea>
                        <div id="description-error" class="text-danger mt-2" style="display: none;"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Skip</button>
                        <button type="button" class="btn btn-primary" onclick="submitSolutionDescription(${challengeId})">
                            Submit Description
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    $('#solutionModal').remove();

    // Add modal to body and show
    $('body').append(modalHtml);
    $('#solutionModal').modal('show');
}

function submitSolutionDescription(challengeId) {
    const description = $('#solution-description').val().trim();

    if (!description) {
        $('#description-error').text('Please provide a description.').show();
        return;
    }

    // Submit description
    $.ajax({
        url: '/api/storyline/solution-description',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            challenge_id: challengeId,
            description: description
        }),
        success: function(response) {
            $('#solutionModal').modal('hide');
            // Show success message
            $('body').append(`
                <div class="alert alert-success alert-dismissible fade show position-fixed" 
                     style="top: 20px; right: 20px; z-index: 9999;">
                    <strong>Success!</strong> Your solution description has been saved.
                    <button type="button" class="close" data-dismiss="alert">
                        <span>&times;</span>
                    </button>
                </div>
            `);

            // Auto-dismiss after 3 seconds
            setTimeout(() => {
                $('.alert-success').alert('close');
            }, 3000);
        },
        error: function(xhr) {
            const error = xhr.responseJSON ? xhr.responseJSON.error : 'Failed to save description';
            $('#description-error').text(error).show();
        }
    });
}

// Admin functions for managing storyline challenges
function updateStorylineChallenge(challengeId, predecessorId, maxLifetime) {
    return $.ajax({
        url: `/api/storyline/challenge/${challengeId}`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            predecessor_id: predecessorId || null,
            max_lifetime: maxLifetime || null
        })
    });
}

// Hook into CTFd's challenge submission success
$(document).ready(function() {
    // Override CTFd's challenge submission handler if it exists
    if (typeof submitChallenge !== 'undefined') {
        const originalSubmitChallenge = submitChallenge;

        window.submitChallenge = function(...args) {
            // Call original function
            const result = originalSubmitChallenge.apply(this, args);

            // If it's a promise, handle success
            if (result && typeof result.then === 'function') {
                result.then(function(response) {
                    if (response && response.success) {
                        // Get challenge info and show modal
                        const challengeId = getCurrentChallengeId();
                        const challengeName = getCurrentChallengeName();
                        if (challengeId && challengeName) {
                            setTimeout(() => {
                                showSolutionDescriptionModal(challengeId, challengeName);
                            }, 1000);
                        }
                    }
                });
            }

            return result;
        };
    }

    // Helper functions to get current challenge info
    function getCurrentChallengeId() {
        // Try to get from URL hash or data attributes
        const hash = window.location.hash;
        const match = hash.match(/#.*-(\d+)$/);
        return match ? parseInt(match[1]) : null;
    }

    function getCurrentChallengeName() {
        // Try to get from page title or challenge title element
        const titleElement = $('.challenge-name, .modal-title, h3');
        return titleElement.length ? titleElement.first().text().trim() : 'this challenge';
    }
});

// Add navigation link to storyline graph
$(document).ready(function() {
    // Add storyline link to navbar if it doesn't exist
    if ($('.navbar-nav a[href="/storyline-graph"]').length === 0) {
        const storylineLink = `
            <li class="nav-item">
                <a class="nav-link" href="/storyline-graph">
                    <i class="fas fa-project-diagram"></i> Storyline
                </a>
            </li>
        `;

        // Try to add after challenges link
        const challengesItem = $('.navbar-nav a[href="/challenges"]').closest('li');
        if (challengesItem.length > 0) {
            challengesItem.after(storylineLink);
        } else {
            // Add to end of navbar
            $('.navbar-nav').append(storylineLink);
        }
    }
});
