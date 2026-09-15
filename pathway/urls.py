from django.urls import path

from . import views


app_name = 'pathway'


urlpatterns = [

    path(
        '',
        views.pathway_manager,
        name='pathway_manager',
    ),

    path(
        'athlete/<int:athlete_id>/',
        views.athlete_pathway_editor,
        name='athlete_pathway_editor',
    ),

    path(
        'athlete/<int:athlete_id>/requirements/',
        views.athlete_pathway_requirements,
        name='athlete_pathway_requirements',
    ),

    path(
        'requirement/<int:requirement_id>/update/',
        views.update_athlete_pathway_requirement,
        name='update_athlete_pathway_requirement',
    ),


    path(
        'athlete/<int:athlete_id>/requirements/save-all/',
        views.bulk_update_athlete_pathway_requirements,
        name='bulk_update_athlete_pathway_requirements',
    ),

    path(
        'overview/',
        views.pathway_overview,
        name='pathway_overview',
    ),

    path(
        'overview/level/<int:level_id>/',
        views.pathway_level_detail,
        name='pathway_level_detail',
    ),



    path(
        'routine-element/<int:element_id>/delete/',
        views.delete_routine_element,
        name='delete_routine_element',
    ),

    path(
        'athlete/<int:athlete_id>/d-score/bars/',
        views.bars_d_score_calculator,
        name='bars_d_score_calculator',
    ),

    path(
        'athlete/<int:athlete_id>/d-score/beam/',
        views.beam_d_score_calculator,
        name='beam_d_score_calculator',
    ),


    path(
        'athlete/<int:athlete_id>/d-score/floor/',
        views.floor_d_score_calculator,
        name='floor_d_score_calculator',
    ),


    path(
        'athlete/<int:athlete_id>/d-score/vault/',
        views.vault_d_score_calculator,
        name='vault_d_score_calculator',
    ),

    path(
        'athlete/<int:athlete_id>/d-score/',
        views.athlete_d_score_dashboard,
        name='athlete_d_score_dashboard',
    ),
]