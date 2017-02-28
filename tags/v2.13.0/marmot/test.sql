SELECT 
    *
FROM
    workflow_workflowhistory
        JOIN
    (SELECT 
        state_id, MAX(id) AS latest
    FROM
        workflow_workflowhistory
    GROUP BY workflowactivity_id) b ON (workflow_workflowhistory.id = b.latest
        AND app_progress.state = 9);


SELECT 
    workflow_workflowhistory.workflowactivity_id, workflow_workflowhistory.state_id
FROM
    workflow_workflowhistory
       INNER JOIN
    (SELECT 
		MAX(id) AS latest
    FROM
        workflow_workflowhistory
    GROUP BY workflowactivity_id) b ON workflow_workflowhistory.id = b.latest;


SELECT 
	workflow_workflowhistory.workflowactivity_id, workflow_workflowhistory.state_id
FROM
	workflow_workflowhistory
	INNER JOIN
	(SELECT 
		MAX(id) AS latest
	FROM
		workflow_workflowhistory
	GROUP BY workflowactivity_id) b
WHERE 
	workflow_workflowhistory.id = b.latest;


SELECT 
    task_task.id, task_task.workflowactivity_id, workflow_workflowhistory.state_id
FROM
    task_task
        INNER JOIN
    workflow_workflowhistory ON (task_task.workflowactivity_id = workflow_workflowhistory.workflowactivity_id)
        RIGHT JOIN
    (SELECT 
        MAX(id) AS latest
    FROM
        workflow_workflowhistory
    GROUP BY workflowactivity_id) U0 ON (workflow_workflowhistory.id = U0.latest);


SELECT 
    `workflow_state`.`id`
FROM
    `workflow_state`
        LEFT OUTER JOIN
    `workflow_state_users` ON (`workflow_state`.`id` = `workflow_state_users`.`state_id`)
        LEFT OUTER JOIN
    `workflow_state_groups` ON (`workflow_state`.`id` = `workflow_state_groups`.`state_id`)
        INNER JOIN
    `workflow_workflow` ON (`workflow_state`.`workflow_id` = `workflow_workflow`.`id`)
WHERE
    (`workflow_state_users`.`user_id` = 3
        OR (`workflow_state_groups`.`group_id`) IN (SELECT 
            U1.`id`
        FROM
            `auth_group` U1
                INNER JOIN
            `auth_user_groups` U2 ON (U1.`id` = U2.`group_id`)
        WHERE
            U2.`user_id` = 3));


SELECT 
    `workflow_state`.`id`,
    `workflow_state`.`name`,
    `workflow_state`.`description`,
    `workflow_state`.`is_start_state`,
    `workflow_state`.`is_end_state`,
    `workflow_state`.`workflow_id`
FROM
    `workflow_state`
        LEFT OUTER JOIN
    `workflow_state_users` ON (`workflow_state`.`id` = `workflow_state_users`.`state_id`)
        LEFT OUTER JOIN
    `workflow_state_groups` ON (`workflow_state`.`id` = `workflow_state_groups`.`state_id`)
        INNER JOIN
    `workflow_workflow` ON (`workflow_state`.`workflow_id` = `workflow_workflow`.`id`)
WHERE
    (`workflow_state_users`.`user_id` = 3
        OR (`workflow_state_groups`.`group_id`) IN (SELECT 
            U0.`id`
        FROM
            `auth_group` U0
                INNER JOIN
            `auth_user_groups` U1 ON (U0.`id` = U1.`group_id`)
        WHERE
            U1.`user_id` = 3));


SELECT 
    `task_task`.`id`,
    `task_task`.`workflowactivity_id`,
    `task_task`.`content_type_id`,
    `task_task`.`object_id`,
    `task_task`.`create_time`,
    MAX(`workflow_workflowhistory`.`id`) AS `latest_history`
FROM
    `task_task`
        LEFT OUTER JOIN
    `workflow_workflowactivity` ON (`task_task`.`workflowactivity_id` = `workflow_workflowactivity`.`id`)
        LEFT OUTER JOIN
    `workflow_workflowhistory` ON (`workflow_workflowactivity`.`id` = `workflow_workflowhistory`.`workflowactivity_id`)
GROUP BY `task_task`.`id`;
