$(document).ready(function() {
    // Добавление новой услуги
    $('#save-procedure').click(function() {
        const section_id = $('#section_id').val();
        const duration = $('#duration').val();
        const base_price = $('#base_price').val();
        const discount = $('#discount').val();
        
        // Собираем переводы
        const translations = [
            {
                lang: 'UKR',
                name: $('#name_ukr').val(),
                description: $('#description_ukr').val()
            }
        ];
        
        // Добавляем необязательные переводы, если они заполнены
        if ($('#name_eng').val()) {
            translations.push({
                lang: 'ENG',
                name: $('#name_eng').val(),
                description: $('#description_eng').val()
            });
        }
        
        if ($('#name_por').val()) {
            translations.push({
                lang: 'POR',
                name: $('#name_por').val(),
                description: $('#description_por').val()
            });
        }
        
        if ($('#name_rus').val()) {
            translations.push({
                lang: 'RUS',
                name: $('#name_rus').val(),
                description: $('#description_rus').val()
            });
        }
        
        // Отправляем данные на сервер
        $.ajax({
            url: '/api/v2/procedures',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                section_id: parseInt(section_id),
                duration: parseInt(duration),
                base_price: parseFloat(base_price),
                discount: parseInt(discount),
                translations: translations
            }),
            beforeSend: function(xhr) {
                xhr.setRequestHeader('Authorization', 'Bearer ' + localStorage.getItem('token'));
            },
            success: function(response) {
                if (response.success) {
                    alert('Услуга успешно добавлена!');
                    $('#add-procedure-modal').modal('hide');
                    location.reload();
                } else {
                    alert('Ошибка: ' + (response.message || 'Неизвестная ошибка'));
                }
            },
            error: function(xhr) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    alert('Ошибка: ' + (response.message || xhr.statusText));
                } catch (e) {
                    alert('Ошибка: ' + xhr.statusText);
                }
            }
        });
    });
    
    // Открытие модального окна для редактирования
    $('.edit-procedure').click(function() {
        const procedureId = $(this).data('id');
        
        $.ajax({
            url: `/api/v2/procedures/${procedureId}`,
            type: 'GET',
            beforeSend: function(xhr) {
                xhr.setRequestHeader('Authorization', 'Bearer ' + localStorage.getItem('token'));
            },
            success: function(response) {
                if (!response.success) {
                    alert('Ошибка: ' + (response.message || 'Неизвестная ошибка'));
                    return;
                }
                
                const procedure = response.data;
                $('#edit-procedure-id').val(procedureId);
                $('#edit-section_id').val(procedure.section_id);
                $('#edit-duration').val(procedure.duration);
                $('#edit-base_price').val(procedure.base_price);
                $('#edit-discount').val(procedure.discount);
                
                // Очистка полей формы перед заполнением
                $('#edit-name_ukr').val('');
                $('#edit-description_ukr').val('');
                $('#edit-name_eng').val('');
                $('#edit-description_eng').val('');
                $('#edit-name_por').val('');
                $('#edit-description_por').val('');
                $('#edit-name_rus').val('');
                $('#edit-description_rus').val('');
                
                // Заполнение переводов
                if (procedure.translations && Array.isArray(procedure.translations)) {
                    procedure.translations.forEach(translation => {
                        if (translation.lang === 'UKR') {
                            $('#edit-name_ukr').val(translation.name);
                            $('#edit-description_ukr').val(translation.description);
                        } else if (translation.lang === 'ENG') {
                            $('#edit-name_eng').val(translation.name);
                            $('#edit-description_eng').val(translation.description);
                        } else if (translation.lang === 'POR') {
                            $('#edit-name_por').val(translation.name);
                            $('#edit-description_por').val(translation.description);
                        } else if (translation.lang === 'RUS') {
                            $('#edit-name_rus').val(translation.name);
                            $('#edit-description_rus').val(translation.description);
                        }
                    });
                }
                
                $('#edit-procedure-modal').modal('show');
            },
            error: function(xhr) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    alert('Ошибка: ' + (response.message || xhr.statusText));
                } catch (e) {
                    alert('Ошибка: ' + xhr.statusText);
                }
            }
        });
    });
    
    // Сохранение изменений услуги
    $('#save-procedure-changes').click(function() {
        const procedureId = $('#edit-procedure-id').val();
        const section_id = $('#edit-section_id').val();
        const duration = $('#edit-duration').val();
        const base_price = $('#edit-base_price').val();
        const discount = $('#edit-discount').val();
        
        // Собираем переводы
        const translations = [
            {
                lang: 'UKR',
                name: $('#edit-name_ukr').val(),
                description: $('#edit-description_ukr').val()
            }
        ];
        
        // Добавляем необязательные переводы, если они заполнены
        if ($('#edit-name_eng').val()) {
            translations.push({
                lang: 'ENG',
                name: $('#edit-name_eng').val(),
                description: $('#edit-description_eng').val()
            });
        }
        
        if ($('#edit-name_por').val()) {
            translations.push({
                lang: 'POR',
                name: $('#edit-name_por').val(),
                description: $('#edit-description_por').val()
            });
        }
        
        if ($('#edit-name_rus').val()) {
            translations.push({
                lang: 'RUS',
                name: $('#edit-name_rus').val(),
                description: $('#edit-description_rus').val()
            });
        }
        
        // Отправляем данные на сервер
        $.ajax({
            url: `/api/v2/procedures/${procedureId}`,
            type: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({
                section_id: parseInt(section_id),
                duration: parseInt(duration),
                base_price: parseFloat(base_price),
                discount: parseInt(discount),
                translations: translations
            }),
            beforeSend: function(xhr) {
                xhr.setRequestHeader('Authorization', 'Bearer ' + localStorage.getItem('token'));
            },
            success: function(response) {
                if (response.success) {
                    alert('Услуга успешно обновлена!');
                    $('#edit-procedure-modal').modal('hide');
                    location.reload();
                } else {
                    alert('Ошибка: ' + (response.message || 'Неизвестная ошибка'));
                }
            },
            error: function(xhr) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    alert('Ошибка: ' + (response.message || xhr.statusText));
                } catch (e) {
                    alert('Ошибка: ' + xhr.statusText);
                }
            }
        });
    });
    
    // Удаление услуги
    $('.delete-procedure').click(function() {
        const procedureId = $(this).data('id');
        
        if (confirm('Вы уверены, что хотите удалить эту услугу?')) {
            $.ajax({
                url: `/api/v2/procedures/${procedureId}`,
                type: 'DELETE',
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('Authorization', 'Bearer ' + localStorage.getItem('token'));
                },
                success: function(response) {
                    if (response.success) {
                        alert('Услуга успешно удалена!');
                        location.reload();
                    } else {
                        alert('Ошибка: ' + (response.message || 'Неизвестная ошибка'));
                    }
                },
                error: function(xhr) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        alert('Ошибка: ' + (response.message || xhr.statusText));
                    } catch (e) {
                        alert('Ошибка: ' + xhr.statusText);
                    }
                }
            });
        }
    });
});
