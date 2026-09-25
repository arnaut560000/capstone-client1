<main class="auth-card">
    <a class="brand" href="index.php">
        <span class="brand-mark"><?= icon('records') ?></span>
        <span>OSY<span class="brand-light">connect</span></span>
    </a>
    <header class="auth-heading">
        <span class="eyebrow">ADMIN PORTAL</span>
        <h1><?= $page === 'setup' ? 'Create your account' : 'Welcome back' ?></h1>
        <p><?= $page === 'setup' ? 'Set up your administrator account to get started.' : 'Sign in to manage your community’s youth records.' ?></p>
    </header>
    <?php if ($errors): ?>
        <div class="alert" role="alert">
            <?php foreach ($errors as $item): ?><p><?= e($item) ?></p><?php endforeach; ?>
        </div>
    <?php endif; ?>
    <form method="post" class="account-form" autocomplete="<?= $page === 'setup' ? 'off' : 'on' ?>">
        <?= csrf() ?>
        <label for="account-username">Username</label>
        <input id="account-username" name="username" required maxlength="50"
               autocomplete="<?= $page === 'setup' ? 'off' : 'username' ?>"
               value="<?= e($_POST['username'] ?? '') ?>" autocapitalize="none" spellcheck="false">
        <label for="account-password">Password</label>
        <input id="account-password" type="password" name="password" required
               <?= $page === 'setup' ? 'minlength="8" maxlength="72" aria-describedby="password-help"' : '' ?>
               autocomplete="<?= $page === 'setup' ? 'new-password' : 'current-password' ?>">
        <?php if ($page === 'setup'): ?>
            <small id="password-help" class="account-help">Use 8–72 characters.</small>
            <label for="account-confirm-password">Confirm password</label>
            <input id="account-confirm-password" type="password" name="confirm_password"
                   required minlength="8" maxlength="72" autocomplete="new-password">
        <?php endif; ?>
        <button class="button primary" type="submit">
            <?= $page === 'setup' ? 'Create account' : 'Sign in' ?> <?= icon('arrow') ?>
        </button>
    </form>
    <p class="auth-footnote">Authorized administrator access only</p>
</main>
