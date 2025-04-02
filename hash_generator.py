from werkzeug.security import generate_password_hash

# Замени 'TwojeHaslo123' на желаемый пароль администратора
plain_password = '123123123123Rr!'
hashed = generate_password_hash(plain_password)
print("Hashed password:", hashed)
