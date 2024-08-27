$(document).ready(function () {
    // 注册逻辑
    $('#signup-form').on('click', '.submit', function (event) {
        event.preventDefault();
        const username = $('#signup-username').val();
        const email = $('#signup-email').val();
        const password = $('#signup-password').val();
        const repeatPassword = $('#signup-repeat-password').val();

        if (password !== repeatPassword) {
            alert('密码不匹配');
            return;
        }

        $.ajax({
            url: '/users/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: username,
                email: email,
                password: password
            }),
            success: function (response) {
                alert('注册成功！请登录。');
                $('#signin').click();
            },
            error: function (error) {
                alert('注册失败：' + error.responseJSON.detail);
            }
        });
    });

    // 登录逻辑
    $('#signin-form').on('click', '.submit', function (event) {
        event.preventDefault();

        const username = $('#signin-username').val();
        const password = $('#signin-password').val();

        if (!username || !password) {
            alert('请输入用户名和密码');
            return;
        }

        $.ajax({
            url: '/users/login',
            type: 'POST',
            contentType: "application/x-www-form-urlencoded",  // 发送表单数据格式
            data: new URLSearchParams({ username: username, password: password }).toString(),  // 转换为字符串
            success: function (response) {
                // 从响应中获取 token
                const token = response.token.access_token;

                // 将 token 存储到 localStorage
                localStorage.setItem('accessToken', token);

                // 可选：你也可以存储其他用户信息
                localStorage.setItem('userUuid', response.user.uuid);

                alert('登录成功！');
                window.location.href = '/';  // 登录成功后重定向到首页
            },
            error: function (error) {
                const errorMessage = error.responseJSON ? error.responseJSON.detail : '未知错误';
                alert('登录失败：' + errorMessage);
            }
        });
    });
});
